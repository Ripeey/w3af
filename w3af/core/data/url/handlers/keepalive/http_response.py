import http.client
from io import StringIO

from .utils import debug
from w3af.core.data.constants.response_codes import NO_CONTENT
from w3af.core.data.kb.config import cf

def close_on_error(read_meth):
    """
    Decorator function. When calling decorated `read_meth` if an error occurs
    we'll proceed to invoke `inst`'s close() method.
    """
    def new_read_meth(inst):
        try:
            return read_meth(inst)
        except http.client.HTTPException:
            inst.close()
            raise
    return new_read_meth


class HTTPResponse(http.client.HTTPResponse):
    # we need to subclass HTTPResponse in order to
    #
    # 1) add readline() and readlines() methods
    # 2) add close_connection() methods
    # 3) add info() and geturl() methods
    # 4) handle cases where the remote server returns two content-length
    #    headers

    # in order to add readline(), read must be modified to deal with a
    # buffer.  example: readline must read a buffer and then spit back
    # one line at a time.  The only real alternative is to read one
    # BYTE at a time (ick).  Once something has been read, it can't be
    # put back (ok, maybe it can, but that's even uglier than this),
    # so if you THEN do a normal read, you must first take stuff from
    # the buffer.

    # the read method wraps the original to accommodate buffering,
    # although read() never adds to the buffer.
    # Both readline and readlines have been stolen with almost no
    # modification from socket.py

    def __init__(self, sock, debuglevel=0, method=None):
        http.client.HTTPResponse.__init__(self, sock, debuglevel, method=method)
        self.fileno = sock.fileno
        self.code = None
        self._rbuf = b''
        self._rbufsize = 8096
        self._handler = None     # inserted by the handler later
        self._host = None        # (same)
        self._url = None         # (same)
        self._connection = None  # (same)
        self._method = method
        self._multiread = None
        self._encoding = None
        self._time = None

    def geturl(self):
        return self._url

    URL = property(geturl)

    def get_encoding(self):
        return self._encoding

    def set_encoding(self, enc):
        self._encoding = enc

    encoding = property(get_encoding, set_encoding)

    def set_wait_time(self, t):
        self._time = t

    def get_wait_time(self):
        return self._time

    def _raw_read(self, amt=None):
        """
        This is the original read function from httplib with a minor
        modification that allows me to check the size of the file being
        fetched, and throw an exception in case it is too big.
        """
        if self.fp is None:
            return ''

        max_file_size = cf.get('max_file_size') or None
        if max_file_size and self.length:
            if self.length > max_file_size:
                self.status = NO_CONTENT
                self.reason = 'No Content'  # Reason-Phrase
                self.close()
                return ''
        # patchFIX if lenght is None then amt is None, also _readall_chunked() or peak_chunked()
        if self.chunked:
            return self._readall_chunked()

        if amt is None:
            # unbounded read
            if self.length is None:
                s = self.fp.read()
            else:
                s = self._safe_read(self.length)
                self.length = 0
            self.close()        # we read everything
            return s

        if self.length is not None:
            if amt > self.length:
                # clip the read to the "end of response"
                amt = self.length

        # we do not use _safe_read() here because this may be a .will_close
        # connection, and the user is reading more bytes than will be provided
        # (for example, reading in 1k chunks)
        s = self.fp.read(amt)
        if self.length is not None:
            self.length -= len(s)

        return s

    def begin(self):
        """
        Updated as 3.9 http/client.py
        """
        if self.msg is not None:
            # we've already started reading the response
            return
        # read until we get a non-100 response
        while True:
            version, status, reason = self._read_status()
            if status != http.client.CONTINUE:
                break
            # skip the header from the 100 response
            while True:
                skipped_headers = http.client._read_headers(self.fp)
                if self.debuglevel > 0:
                    print("header:", skipped_headers)

        self.status = status
        self.reason = reason.strip()
        if version == 'HTTP/1.0':
            self.version = 10
        elif version.startswith('HTTP/1.'):
            self.version = 11   # use HTTP/1.1 code for HTTP/1.x where x>=1
        elif version == 'HTTP/0.9':
            self.version = 9
        else:
            raise http.client.UnknownProtocol(version)

        # remove in python 3.9 but will keep it for no reason (who is this old anyway?)

        if self.version == 9:
            self.length = None
            self.chunked = 0
            self.will_close = 1
            
            self.msg = http.client.parse_headers(StringIO())
            return

        # patchFIX: headers can contain multiple same key, check: concat at NonRepeatKeyValueContainer in Header class with ','' or ' '
        # which is already done with http.client.getheader(self, name, default=None)
        # for now were doing ^ here and not over Headers() class
        # if we get any issues will shift to NonRepeatKeyValueContainer Header() class instead with a patch setter before super() __init__
        self.headers = self.msg = http.client.parse_headers(self.fp)
        # to understand this see: email.message.Message
        for hdr in self.headers.keys():
            val = self.getheader(hdr)
            del self.headers[hdr]
            self.headers.__setitem__(hdr, val)

        if self.debuglevel > 0:
            for hdr, val in self.headers.items():
                print("header:", hdr + ":", val)

        # I think by default now it doesn't
        """
        # don't let the msg keep an fp
        self.msg.fp = None
        """

        # are we using the chunked-style of transfer encoding?
        tr_enc = self.headers.get("transfer-encoding")
        if tr_enc and tr_enc.lower() == "chunked":
            self.chunked = True
            self.chunk_left = None
        else:
            self.chunked = False

        # will the connection close at the end of the response?
        self.will_close = self._check_close()

        # do we have a Content-Length?
        # NOTE: RFC 2616, S4.4, #3 says we ignore this if tr_enc is "chunked"
        self.length = None
        length = self.headers.get("content-length")
        if length and not self.chunked:
            try:
                self.length = int(length)
            except ValueError:
                self.length = None
            else:
                if self.length < 0:  # ignore nonsensical negative lengths
                    self.length = None
        else:
            self.length = None

        # does the body have a fixed length? (of zero)
        if (status == NO_CONTENT or status == http.client.NOT_MODIFIED or
            100 <= status < 200 or      # 1xx codes
            self._method == 'HEAD'):
            self.length = 0

        # if the connection remains open, and we aren't using chunked, and
        # a content-length was not provided, then assume that the connection
        # WILL close.
        if not self.will_close and \
           not self.chunked and \
           self.length is None:
            self.will_close = True
    # Probably dont need anymore
    '''
    def _get_content_length(self):
        """
        Some very strange sites will return two content-length headers. By
        default urllib2 will concatenate the two values using commas. Then
        when the value needs to be used... everything fails.

        This method tries to solve the issue by returning the lower value
        from the list. Sadly some bytes might be ignored, but it is much
        better than raising exceptions.

        :return: The content length (as integer)
        """
        length = self.headers.get('content-length')

        if length is None:
            # This is a response where there is no content-length header,
            # most likely a chunked response
            return None

        split = length.split(',')
        split = [int(cl) for cl in split]
        return min(split)
    '''
    def close(self):
        # First call parent's close()
        http.client.HTTPResponse.close(self)
        if self._handler:
            self._handler._request_closed(self._connection)

    def close_connection(self):
        self._handler._remove_connection(self._connection)
        self.close()

    def info(self):
        # pylint: disable=E1101
        return self.headers
        # pylint: enable=E1101

    @close_on_error
    def read(self, amt=None):
        # w3af does always read all the content of the response, and I also need
        # to do multiple reads to this response...
        #
        # TODO: Is this OK? What if a HEAD method actually returns something?!
        if self._method == 'HEAD':
            # This indicates that we have read all that we needed from the socket
            # and that the socket can be reused!
            #
            # This like fixes the bug with title "GET is much faster than HEAD".
            # https://sourceforge.net/tracker2/?func=detail&aid=2202532&group_id=170274&atid=853652
            self.close()
            return b''

        if self._multiread is None:
            # read all
            self._multiread = self._raw_read()

        if amt is not None:
            L = len(self._rbuf)
            if amt > L:
                amt -= L
            else:
                s = self._rbuf[:amt]
                self._rbuf = self._rbuf[amt:]
                return s
        else:
            s = self._rbuf + self._multiread
            self._rbuf = b''
            return s

    def readline(self, limit=-1):
        i = self._rbuf.find('\n')

        while i < 0 and not (0 < limit <= len(self._rbuf)):
            new = self._raw_read(self._rbufsize)
            if not new:
                break
            i = new.find('\n')
            if i >= 0:
                i += len(self._rbuf)
            self._rbuf = self._rbuf + new

        if i < 0:
            i = len(self._rbuf)
        else:
            i += 1

        if 0 <= limit < len(self._rbuf):
            i = limit

        data, self._rbuf = self._rbuf[:i], self._rbuf[i:]
        return data

    @close_on_error
    def readlines(self, sizehint=0):
        total = 0
        line_list = []
        while 1:
            line = self.readline()
            if not line:
                break
            line_list.append(line)
            total += len(line)
            if sizehint and total >= sizehint:
                break
        return line_list

    def set_body(self, data):
        """
        This was added to make my life a lot simpler while implementing mangle
        plugins
        """
        self._multiread = data

    def _check_close(self):
        """
        Overriding to add "max" support
        http://tools.ietf.org/id/draft-thomson-hybi-http-timeout-01.html#p-max
        """
        keep_alive = self.headers.get('keep-alive')

        if keep_alive and keep_alive.lower().endswith('max=1'):
            # We close right before the "max" deadline
            debug('will_close = True due to max=1')
            return True

        conn = self.headers.get('connection')

        # Is the remote end saying we need to keep the connection open?
        if conn and 'keep-alive' in conn.lower():
            debug('will_close = False due to Connection: keep-alive')
            return False

        # Is the remote end saying we need to close the connection?
        elif conn and 'close' in conn.lower():
            debug('will_close = True due to Connection: close')
            return True

        if self.version == 11:
            # An HTTP/1.1 connection is assumed to stay open unless explicitly
            # closed.
            debug('will_close = False due to default keep-alive in 1.1')
            return False

        # Proxy-Connection is a netscape hack.
        pconn = self.headers.get('proxy-connection')
        if pconn and 'keep-alive' in pconn.lower():
            return False

        # otherwise, assume it will close
        return True
