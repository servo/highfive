from eventhandler import EventHandler

MSG = ('We would like to write about this change in the monthly blog post! '
       'We have a few questions about this PR that will make this task '
       'easie :smile:\n\n'
       '1. Who is most impacted by this change: users, '
       'Servo developers, embedders, or some other group?\n'
       '1. What observable difference does this change make?\n'
       '1. What preferences (if any) need to be enabled to observe '
       'this difference?\n'
       '1. What (if any) specific URLs are affected?\n\n'
       'If this change is part of a broader feature/project please '
       'make sure the PR description contains a `Fixes: #12345` or '
       '`Part of: #12345` issue reference.\n\n'
       'Thanks for helping us prepare the monthly blog post! :heart:')


class MonthlyUpdateHandler(EventHandler):
    def on_issue_labeled(self, api, payload):
        if payload['label']['name'].lower() == 'monthly update':
            api.post_comment(MSG)


handler_interface = MonthlyUpdateHandler
