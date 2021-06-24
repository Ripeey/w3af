# -*- coding: utf-8 -*-
from w3af.core.data.constants.encodings import DEFAULT_ENCODING
import hashlib


def gen_hash(request):
    """
    Generate an unique ID for a request

    Note that we use safe_str function in order to avoid errors like:
        * Encoding error #1917
        * https://github.com/andresriancho/w3af/issues/1917
    """
    req = request
    headers_1 = ''.join('%s%s' % (h, v) for h, v in req.headers.items())
    headers_2 = ''.join('%s%s' % (h, v) for h, v in req.unredirected_hdrs.items())
    
    the_str = '%s%s%s%s%s' % (req.get_method(),
                              req.get_full_url(),
                              headers_1,
                              headers_2,
                              req.data or '')
    # patchFIX encoding
    # could be DEFAULT_ENCODING but we removing 'unicode_escape' to prevent conflict
    return hashlib.md5(the_str.encode(DEFAULT_ENCODING)).hexdigest()


# Showing TypeError: Unicode-objects must be encoded before hashing so we doing bytes all [patchFIX]
'''
def safe_str(obj):
    """
    http://code.activestate.com/recipes/466341-guaranteed-conversion-to-unicode-or-byte-string/

    :return: The byte string representation of obj
    """
    try:
        return str(obj)
    except UnicodeEncodeError:
        # obj is unicode
        return str(obj).encode('unicode_escape')
'''