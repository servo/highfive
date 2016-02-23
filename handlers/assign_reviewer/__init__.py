from eventhandler import EventHandler
import re

# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(commit_msg):
    reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
    match = reviewer_re.search(commit_msg)
    if not match:
        return None
    return match.group(1)

class AssignReviewerHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        reviewer = find_reviewer(payload["pull_request"]["body"])
        if reviewer:
            api.set_assignee(reviewer)

    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        reviewer = find_reviewer(payload["comment"]["body"])
        if reviewer:
            api.set_assignee(reviewer)


handler_interface = AssignReviewerHandler
