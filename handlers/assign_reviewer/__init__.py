from eventhandler import EventHandler
from helpers import get_collaborators
import re

WELCOME_MSG = ("Thanks for the pull request, and welcome! "
               "The Servo team is excited to review your changes, "
               "and you should hear from @%s (or someone else) soon.")


def find_reviewer(comment, collaborators):
    """
    If the user specified a reviewer, return the username,
    otherwise returns None.
    """
    reviewer = re.search(r'.*r\?[:\- ]*@([a-zA-Z0-9\-]*)', comment)
    if reviewer and reviewer.group(1) in collaborators:
        return reviewer.group(1)
    return None


def get_approver(payload, collaborators):
    user = payload['comment']['user']['login']
    comment = payload['comment']['body']
    approval_regex = r'.*@bors-servo[: ]*r([\+=])([a-zA-Z0-9\-]*)'
    approval = re.search(approval_regex, comment)

    if approval and user in collaborators:
        if approval.group(1) == '=':  # "r=username"
            reviewer = approval.group(2)
            if reviewer in collaborators:
                return reviewer
        return user  # fall back and assign the approver
    return None


class AssignReviewerHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        pr = payload["pull_request"]
        collaborators = get_collaborators(api)
        # If the pull request already has an assignee,
        # don't try to set one ourselves.
        if pr["assignee"] is not None:
            return

        # Find a reviewer from PR comment (like "r? username"),
        # or assign one ourselves.
        if not collaborators:
            return

        reviewer = find_reviewer(pr["body"], collaborators) or \
            collaborators[pr["number"] % len(collaborators)]
        api.set_assignee(reviewer)

        # Add welcome message for new contributors.
        author = pr['user']['login']
        if api.is_new_contributor(author):
            api.post_comment(WELCOME_MSG % reviewer)

    def on_new_comment(self, api, payload):
        collaborators = get_collaborators(api)
        if not self.is_open_pr(payload):
            return

        # If this is an approval comment from a reviewer, then assign them
        reviewer = get_approver(payload, collaborators)
        if reviewer:
            api.set_assignee(reviewer)
            return

        reviewer = find_reviewer(payload["comment"]["body"], collaborators)
        if reviewer:
            api.set_assignee(reviewer)


handler_interface = AssignReviewerHandler
