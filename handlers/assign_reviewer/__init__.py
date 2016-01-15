from eventhandler import EventHandler
import re

on_pr_opened = "Thanks for the pull request! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."

# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(commit_msg):
    reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
    match = reviewer_re.search(commit_msg)
    if not match:
        return None
    return match.group(1)

class AssignReviewerHandler(EventHandler):
    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        reviewer = find_reviewer(payload["comment"]["body"])
        if reviewer:
            api.set_assignee(reviewer)
# on_pr_opened is for https://github.com/servo/highfive/issues/40
    def on_pr_opened(self, api, payload):
        pr_opened = payload['action']
        if pr_opened == 'created':
            collaborators = ['jdm', 'larsbergstrom', 'metajack', 'mbrubeck',
                             'Ms2get', 'Manishearth', 'glennw', 'pcwalton',
                             'SimonSapin']
            random.seed()
            to_notify = random.choice(collaborators)
            api.post_comment(pr_opened % to_notify)

handler_interface = AssignReviewerHandler
