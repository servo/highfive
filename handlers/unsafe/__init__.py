from eventhandler import EventHandler

unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'

class UnsafeHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++') and line.find('unsafe ') > -1:
                self.warn(unsafe_warning_msg)
                return


handler_interface = UnsafeHandler
