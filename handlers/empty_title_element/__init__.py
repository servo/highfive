from __future__ import absolute_import
from eventhandler import EventHandler

WARNING = ("These commits include an empty title element (`<title></title>`). "
           "Consider adding appropriate metadata.")


class EmptyTitleElementHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        for line in api.get_added_lines():
            if line.find("<title></title>") > -1:
                # This test doesn't consider case and whitespace the same way
                # that a HTML parser does, so empty title elements might still
                # go unnoticed. It will catch the low-hanging fruit, though.
                self.warn(WARNING)
                return


handler_interface = EmptyTitleElementHandler
