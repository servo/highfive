from __future__ import absolute_import

import re

from eventhandler import EventHandler
from helpers import get_collaborators

WELCOME_MSG = ("Thanks for the pull request, and welcome! "
               "The Servo team is excited to review your changes, "
               "and you should hear from @%s (or someone else) soon.")


def find_reviewer(comment):
    """
    If the user specified a reviewer, return the username,
    otherwise returns None.
    """
    reviewer = re.search(r'.*r\?[:\- ]*@?([a-zA-Z0-9\-]+)', str(comment))
    if reviewer:
        return reviewer.group(1)
    return None


def choose_reviewer(pr, collaborators):
    """
    Choose a (pseudo-)random reviewer from the collaborators, who is not the
    author. If there are no collaborators other than the author, return None.
    """
    author = pr['user']['login'].lower()
    # Avoid using sets to maintain the order of reviewers and
    # thus ensure an even rotation of reviewers
    potential_reviewers = [collaborator for collaborator in collaborators
                           if collaborator != author]
    if not potential_reviewers:
        return None
    return potential_reviewers[pr['number'] % len(potential_reviewers)]


def get_approver(payload):
    user = payload['comment']['user']['login']
    comment = payload['comment']['body']
    approval_regex = r'.*@bors-servo[: ]*r([\+=])([a-zA-Z0-9\-]*)'
    approval = re.search(approval_regex, str(comment))

    if approval:
        if approval.group(1) == '=':  # "r=username"
            reviewer = approval.group(2)
            return reviewer
        return user  # fall back and assign the approver
    return None


class AssignReviewerHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        pr = payload["pull_request"]
        # If the pull request already has an assignee,
        # don't try to set one ourselves.
        if pr["assignee"] != None:      # NOQA (silence flake8 here)
            return

        reviewer = find_reviewer(pr["body"])

        # Find a reviewer from PR comment (like "r? username"),
        # or assign one ourselves.
        if not reviewer:
            collaborators = get_collaborators(api)
            if not collaborators:
                return
            reviewer = choose_reviewer(pr, collaborators)

        if not reviewer:
            return

        api.set_assignee(reviewer)

        # Add welcome message for new contributors.
        author = pr['user']['login']
        if api.is_new_contributor(author):
            api.post_comment(WELCOME_MSG % reviewer)

    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        # If this is an approval comment from a reviewer, then assign them
        reviewer = get_approver(payload)
        if reviewer:
            api.set_assignee(reviewer)
            return

        reviewer = find_reviewer(payload["comment"]["body"])
        if reviewer:
            api.set_assignee(reviewer)


handler_interface = AssignReviewerHandler
