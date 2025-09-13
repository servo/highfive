from __future__ import absolute_import

from configparser import ConfigParser
import os.path
import time

from eventhandler import EventHandler

AWAITING_MERGE = "S-awaiting-merge"
AWAITING_REVIEW = "S-awaiting-review"
NEED_CODE_CHANGES = "S-needs-code-changes"
NEED_REBASE = "S-needs-rebase"
TESTS_FAILED = "S-tests-failed"

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


def clear_pr_labels(api):
    labels = api.get_labels()

    for label in [
        AWAITING_MERGE,
        TESTS_FAILED,
        NEED_CODE_CHANGES,
        NEED_REBASE,
    ]:
        if label in labels:
            api.remove_label(label)


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


def update_rebase_status(api, payload):
    if "pull_request" not in payload:
        return

    mergeable = payload['pull_request']['mergeable']

    # If mergeable is null, the data wasn't available yet.
    # Once it is, mergeable will be either true or false.
    while mergeable is None:
        time.sleep(1)  # wait for GitHub to finish determine mergeability
        pull_request = api.get_pull()
        mergeable = pull_request['mergeable']

    if mergeable == False: # noqa
        api.add_label(NEED_REBASE)


def is_draft_pr(payload):
    return "pull_request" in payload and \
        payload["pull_request"]["draft"] == True # noqa


class StatusUpdateHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        if is_draft_pr(payload):
            return

        labels = api.get_labels()
        if AWAITING_REVIEW not in labels:
            api.add_label(AWAITING_REVIEW)
        update_rebase_status(api, payload)
        handle_custom_labels(api, 'opened')

    def on_pr_updated(self, api, payload):
        if is_draft_pr(payload):
            return

        clear_pr_labels(api)
        api.add_label(AWAITING_REVIEW)
        update_rebase_status(api, payload)
        handle_custom_labels(api, 'updated')

    def on_pr_closed(self, api, payload):
        handle_custom_labels(api, 'closed')
        if "pull_request" in payload and \
           payload['pull_request']['merged'] == True: # noqa
            api.remove_label(AWAITING_MERGE)
            handle_custom_labels(api, 'merged')

    def on_pr_enqueued(self, api, payload):
        clear_pr_labels(api)
        api.add_label(AWAITING_MERGE)
        handle_custom_labels(api, 'enqueued')

    def on_pr_dequeued(self, api, payload):
        labels = api.get_labels()
        update_rebase_status(api, payload)
        if payload["reason"] != "MERGE":
            if AWAITING_MERGE in labels:
                api.remove_label(AWAITING_MERGE)
            if payload["reason"] == "CI_FAILURE":
                api.add_label(TESTS_FAILED)
        handle_custom_labels(api, 'dequeued')


handler_interface = StatusUpdateHandler
