"""
utils.py

Copyright 2006 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import sys


def verify_python_version():
    """
    Check python version eq 3.6 or higher
    """
    major, minor, micro, release_level, serial = sys.version_info
    if major == 3:
        if minor <= 6:
            msg = 'Error: Python 3.%s found but Python 3.6 or higher required.'
            print((msg % minor))
    elif major < 3:
        msg = ('It seems that you are running w3af using Python2, which is not'
               ' supported in python-3 version of w3af.\nTo force w3af to be'
               ' run using python3 run it as follows (depending on your OS):'
               '\n\n'
               ' * python3 w3af_console\n'
               ' * python3 w3af_console\n'
               '\n'
               'To make this change permanent modify the shebang line in the'
               ' w3af_console, w3af_gui and w3af_api scripts.')
        print(msg)
        sys.exit(1)


def running_in_virtualenv():
    if hasattr(sys, 'real_prefix'):
        return True

    return False