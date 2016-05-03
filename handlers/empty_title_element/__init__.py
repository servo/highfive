from eventhandler import EventHandler
from helpers import is_addition

WARNING = ("These commits include an empty title element, '<title></title>'. "
           "Consider adding appropriate metadata.")


class EmptyTitleElementHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        for line in diff.split('\n'):
            if is_addition(line) and line.find("<title></title>") > -1:
                # This test doesn't consider case and whitespace the same way
                # that a HTML parser does, so empty title elements might still
                # go unnoticed. It will catch the low-hanging fruit, though.
                self.warn(WARNING)
                return


handler_interface = EmptyTitleElementHandler
