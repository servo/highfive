from __future__ import absolute_import

import json
import re

from eventhandler import EventHandler


def check_failure_log(api, bors_comment):
    # bors_comment would be something like,
    # ":broken_heart: Test failed - [linux2](https://build.servo.org/builders/linux2/builds/2627)"  # noqa
    # ... from which we get the relevant build result url
    url = next(iter(re.findall(r'.*\((.*)\)', str(bors_comment))))
    if not url:
        return

    # Substitute and get the new url
    # (e.g. https://build.servo.org/json/builders/linux2/builds/2627)
    json_url = re.sub(r'(.*)(builders/.*)', r'\1json/\2', url)
    json_stuff = api.get_page_content(json_url)
    if not json_stuff:
        return

    build_stats = json.loads(json_stuff)

    build_log = []
    for step in build_stats['steps']:
        if 'failed' in step['text']:
            build_log = step['logs']
            break

    failed_tests_url = None
    failed_summary_url = None
    for (name, log_url) in build_log:
        if name == 'stdio':
            failed_tests_url = log_url + '/text'
        elif 'errorsummary.log' in name:
            failed_summary_url = log_url + '/text'

    if not failed_summary_url and not failed_tests_url:
        return

    failures = None
    if failed_tests_url:
        stdio = api.get_page_content(failed_tests_url)
        failure_regex = r'.*Tests with unexpected results:\n(.*)$'
        failures = next(iter(re.findall(failure_regex, stdio, re.DOTALL)))

    if not failures and failed_summary_url:
        failures = api.get_page_content(failed_summary_url)

    if failures:
        comments = ["Test failures:", "<details>"]
        comments += [' ' * 4 + line for line in failures.split('\n')]
        comments += ["</details>"]
        api.post_comment('\n'.join(comments))


class HomuStatusHandler(EventHandler):
    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        if payload['comment']['user']['login'] != 'bors-servo':
            return

        labels = api.get_labels()
        msg = payload["comment"]["body"]

        def remove_if_exists(label):
            if label in labels:
                api.remove_label(label)

        if 'has been approved by' in msg or 'Testing commit' in msg:
            for label in ["S-awaiting-review", "S-needs-rebase",
                          "S-tests-failed", "S-needs-code-changes",
                          "S-needs-squash", "S-awaiting-answer"]:
                remove_if_exists(label)
            if "S-awaiting-merge" not in labels:
                api.add_label("S-awaiting-merge")

        elif 'Test failed' in msg:
            remove_if_exists("S-awaiting-merge")
            api.add_label("S-tests-failed")
            # Get the homu build stats url,
            # extract the failed tests and post them!
            check_failure_log(api, msg)

        elif 'Please resolve the merge conflicts' in msg:
            remove_if_exists("S-awaiting-merge")
            api.add_label("S-needs-rebase")


handler_interface = HomuStatusHandler
