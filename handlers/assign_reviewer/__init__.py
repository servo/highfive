from eventhandler import EventHandler
import re
import ConfigParser
import os

COLLABORATORS_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../../collaborators.ini')

WELCOME_MSG = "Thanks for the pull request, and welcome! The Servo team is excited to review "\
              "your changes, and you should hear from @%s (or someone else) soon."

def get_collaborators_config():
    config = ConfigParser.ConfigParser()
    config.read(COLLABORATORS_CONFIG_FILE)
    return config

def get_collaborators(api):
    config = get_collaborators_config()
    repo = api.owner + '/' + api.repo

    try:
        return [username for (username, _) in config.items(repo)]
    except ConfigParser.NoSectionError:
        return [] # No collaborators

# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(comment, collaborators):
    reviewer = re.search(r'.*r\?[:\- ]*@([a-zA-Z0-9\-]*)', comment)
    if reviewer and reviewer.group(1) in collaborators:
        return reviewer.group(1)
    return None

def get_approver(payload, collaborators):
    user = payload['comment']['user']['login']
    comment = payload['comment']['body']
    approval = re.search(r'.*@bors-servo[: ]*r([\+=])([a-zA-Z0-9\-]*)', comment)

    if approval and user in collaborators:
        if approval.group(1) == '=':        # check if it's something like "r=username"
            reviewer = approval.group(2)
            if reviewer in collaborators:
                return reviewer
        return user         # fall back and assign the approver
    return None

class AssignReviewerHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        collaborators = get_collaborators(api)
        # If the pull request already has an assignee, don't try to set one ourselves.
        if payload["pull_request"]["assignee"] is not None:
            return

        # find a reviewer from PR comment (like "r? username") or assign one ourselves
        if not collaborators:
            return

        reviewer = find_reviewer(payload["pull_request"]["body"], collaborators) or \
                   collaborators[payload["pull_request"]["number"] % len(collaborators)]
        api.set_assignee(reviewer)

        # Add welcome message for new contributors
        author = payload["pull_request"]['user']['login']
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
