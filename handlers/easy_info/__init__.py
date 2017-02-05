from eventhandler import EventHandler

import re

ASSIGN_MSG = 'assign me'

MSG = ('Hi! If you have any questions regarding this issue, feel free to make'
       ' a comment here, or ask it in the `#servo` channel in '
       '[IRC](https://wiki.mozilla.org/IRC).\n\n'
       'If you intend to work on this issue, then add `@%s: %s`'
       ' to your comment, and I\'ll assign this to you. :smile:')

RESPONSE_FAIL = ('It looks like this has already been assigned to someone.'
                 ' I\'ll leave the decision to a core contributor.')

RESPONSE_OK = ('Hey @%s! Thanks for your interest in working on this issue.'
               ' It\'s now assigned to you!')


class EasyInfoHandler(EventHandler):
    def on_issue_labeled(self, api, payload):
        if payload['label']['name'].lower() == 'e-easy':
            api.post_comment(MSG % (api.user, ASSIGN_MSG))

    def on_new_comment(self, api, payload):
        if payload['issue']['state'] != 'open':
            return

        user = payload['comment']['user']['login']
        if user == api.user:    # ignore comments from self
            return              # (since `MSG` already has `ASSIGN_MSG`)

        msg = payload['comment']['body']

        if re.search(r'@%s[: ]*%s' % (api.user, ASSIGN_MSG), str(msg)):
            labels = payload['issue']['labels']
            if any(l['name'] == 'C-assigned' for l in labels):
                api.post_comment(RESPONSE_FAIL)
                return

            api.add_label('C-assigned')
            api.post_comment(RESPONSE_OK % user)


handler_interface = EasyInfoHandler
