from eventhandler import EventHandler

warning_msg = "These commits include an empty title element, '<title></title>'. Consider adding appropriate metadata."

class EmptyTitleElementHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++') and line.find("<title></title>") > -1:
                # This test doesn't consider case and whitespace in the same way
                # that a HTML parser does, so empty title elements might still
                # go unnoticed. It will catch the low-hanging fruit, though.
                self.warn(warning_msg)
                return


handler_interface = EmptyTitleElementHandler
