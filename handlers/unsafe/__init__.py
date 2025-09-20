from __future__ import absolute_import

from eventhandler import EventHandler


unsafe_warning_msg = ('These commits modify **unsafe code**. '
                      'Please review it carefully!')


class UnsafeHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        return
        for line in api.get_added_lines():
            if line.find('unsafe ') > -1:
                self.warn(unsafe_warning_msg)
                return


handler_interface = UnsafeHandler
