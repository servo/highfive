from __future__ import absolute_import

from eventhandler import EventHandler
from helpers import is_addition


unsafe_warning_msg = ('These commits modify **unsafe code**. '
                      'Please review it carefully!')



class UnsafeHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        for line in self.get_added_lines(api):
            if line.find('unsafe ') > -1:
                self.warn(unsafe_warning_msg)
                return


handler_interface = UnsafeHandler
