from eventhandler import EventHandler
import re
import ConfigParser
import os

COLLABORATORS_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'collaborators.ini')

def get_collaborators_config():
    config = ConfigParser.ConfigParser()
    config.read(COLLABORATORS_CONFIG_FILE)
    return config

# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(commit_msg):
    reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
    match = commit_msg and reviewer_re.search(commit_msg)
    if not match:
        return None
    return match.group(1)

# Return a collaborator's username if there is one in the config file. Otherwise, return None.
def choose_reviewer(api, pull_number):
    config = get_collaborators_config()
    repo = api.owner + '/' + api.repo

    try:
        collaborators = [username for (username, _) in config.items(repo)]
    except ConfigParser.NoSectionError:
        return # No collaborators

    return collaborators and collaborators[pull_number % len(collaborators)]

class AssignReviewerHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        reviewer = find_reviewer(payload["pull_request"]["body"]) \
            or choose_reviewer(api, payload["pull_request"]["number"])
        if reviewer:
            api.set_assignee(reviewer)

    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        reviewer = find_reviewer(payload["comment"]["body"])
        if reviewer:
            api.set_assignee(reviewer)


handler_interface = AssignReviewerHandler
