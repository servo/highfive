from eventhandler import EventHandler


class EasyInfoHandler(EventHandler):
    def on_issue_labeled(self, api, payload):
        if payload['label']['name'].lower() == 'e-easy':
            api.post_comment(('Please make a comment here if you intend to '
                              'work on this issue. Thank you!'))

handler_interface = EasyInfoHandler
