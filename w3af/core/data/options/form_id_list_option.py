"""
form_id_list_option.py

Copyright 2008 Andres Riancho

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
from w3af.core.controllers.exceptions import BaseFrameworkException
from w3af.core.data.options.baseoption import BaseOption
from w3af.core.data.options.option_types import FORM_ID_LIST
from w3af.core.data.parsers.utils.form_id_matcher_list import FormIDMatcherList


class FormIDListOption(BaseOption):
    _type = FORM_ID_LIST

    def set_value(self, value):
        """
        :param value: The value parameter is set by the user interface, which
        for example sends '[]' or '[{}]'

        Based on the value parameter and the option type, I have to create a nice
        looking object like [] or [FormIDMatcher({})].
        """
        if isinstance(value, FormIDMatcherList):
            value = value.to_json()

        self._value = self.validate(value)

    def validate(self, value):
        try:
            return FormIDMatcherList(value)
        except (Exception, e):
            msg = 'Invalid form ID list configured by user, error: %s.' % e
            raise BaseFrameworkException(msg)
