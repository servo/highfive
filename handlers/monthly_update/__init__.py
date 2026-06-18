from eventhandler import EventHandler

import re

REPLY = "monthly update"

REACTION = "eyes"

MSG = ('Someone thinks this change could be added to the monthly blog '
       'post! To help with this, we need someone to answer the following '
       'qurstions: :smile:\n\n'
       '1. Who is most impacted by this change: users, '
       'Servo developers, embedders, or some other group?\n'
       '1. What observable difference does this change make?\n'
       '1. What preferences (if any) need to be enabled to observe '
       'this difference?\n'
       '1. What (if any) specific URLs are affected?\n\n'
       'If this change is part of a broader feature/project please '
       'make sure the PR description contains a `Fixes: #12345` or '
       '`Part of: #12345` issue reference.\n\n'
       'Please add `@%s %s` when answering these '
       'questions so the bot notices your answer (or just quote this '
       'comment).\n\n'
       'Thanks for helping us prepare the monthly blog post! :heart:')


class MonthlyUpdateHandler(EventHandler):
    def on_issue_labeled(self, api, payload):
        if payload['label']['name'].lower() == 'monthly update':
            api.post_comment(MSG % (api.user, REPLY))

    def on_new_comment(self, api, payload):
        if payload['issue']['state'] != 'open':
            return

        user = payload['comment']['user']['login']
        if user == api.user:    # ignore comments from self
            return              # (since `MSG` already has `REPLY`)

        msg = payload['comment']['body']

        if re.search(r'@%s[: ]*%s' % (api.user, REPLY), str(msg)):
            api.add_reaction(payload['comment']['id'], REACTION)


handler_interface = MonthlyUpdateHandler
