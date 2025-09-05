from __future__ import absolute_import

from configparser import ConfigParser
import os.path
import time

from eventhandler import EventHandler


config = ConfigParser()
config.optionxform = str  # Be case sensitive
config.read(os.path.join(os.path.dirname(__file__), 'labels.ini'))
config = {
    repo: {
        event: set(labels.split(' ')) for event, labels in config.items(repo)
    }
    for repo in config.sections()
}
# TODO(aneeshusa): Add checking of config option validity


def manage_pr_state(api, payload):
    labels = api.get_labels()

    for label in [
        "S-awaiting-merge",
        "S-tests-failed",
        "S-needs-code-changes"
    ]:
        if label in labels:
            api.remove_label(label)
    if "S-awaiting-review" not in labels:
        api.add_label("S-awaiting-review")

    if payload["action"] == "synchronize" and "S-needs-rebase" in labels:
        mergeable = payload['pull_request']['mergeable']
        # If mergeable is null, the data wasn't available yet.
        # Once it is, mergeable will be either true or false.
        while mergeable is None:
            time.sleep(1)  # wait for GitHub to finish determine mergeability
            pull_request = api.get_pull()
            mergeable = pull_request['mergeable']

        if mergeable:
            api.remove_label("S-needs-rebase")


def handle_custom_labels(api, event):
    repo_config = config.get('{}/{}'.format(api.owner, api.repo), None)
    if not repo_config:
        return
    labels = api.get_labels()
    for label in repo_config.get('remove_on_pr_{}'.format(event), []):
        if label in labels:
            api.remove_label(label)
    for label in repo_config.get('add_on_pr_{}'.format(event), []):
        if label not in labels:
            api.add_label(label)


class StatusUpdateHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        manage_pr_state(api, payload)
        handle_custom_labels(api, 'opened')

    def on_pr_updated(self, api, payload):
        manage_pr_state(api, payload)
        handle_custom_labels(api, 'updated')

    def on_pr_closed(self, api, payload):
        handle_custom_labels(api, 'closed')
        if payload['pull_request']['merged']:
            api.remove_label("S-awaiting-merge")
            handle_custom_labels(api, 'merged')


handler_interface = StatusUpdateHandler
