from __future__ import absolute_import

import json
import re

from eventhandler import EventHandler

WPT_RESULT_ARROW = '\xe2\x96\xb6'


def parse_log(log):     # gets the names of the failed tests
    test_names = []
    l = log.split()
    for i, thing in enumerate(l):
        if thing == WPT_RESULT_ARROW:
            # We can blindly index the results here, because we can rely
            # on the WPT output. It has the unexpected result, expected result
            # and the test path following that unicode character
            name = l[i + 4].split('/')[-1]
            test_names.append(name)
    return test_names


def get_failed_url(json_obj):
    if not json_obj:
        return

    build_stats = json.loads(json_obj)
    build_log = []
    for step in build_stats['steps']:
        if 'failed' in step['text']:
            build_log = step['logs']
            break

    for (name, log_url) in build_log:
        if name == 'stdio':
            failed_url = log_url
            return failed_url


def get_known_intermittents(api, test_names):
    known_fails = set()     # so that we don't have duplicates
    for name in test_names:
        for issue in api.get_intermittents(name):
            known_fails.add(issue['number'])
    return known_fails


def check_failure_log(api, bors_comment):
    # bors_comment would be something like,
    # ":broken_heart: Test failed - [linux2](http://build.servo.org/builders/linux2/builds/2627)"  # noqa
    # ... from which we get the relevant build result url
    url = iter(re.findall(r'.*\((.*)\)', str(bors_comment))).next()
    if not url:
        return

    # Substitute and get the new url
    # (e.g. http://build.servo.org/json/builders/linux2/builds/2627)
    json_url = re.sub(r'(.*)(builders/.*)', r'\1json/\2', url)
    json_stuff = api.get_page_content(json_url)
    failed_url = get_failed_url(json_stuff)
    if not failed_url:
        return

    stdio = api.get_page_content(failed_url)
    failure_regex = r'.*Tests with unexpected results:\n(.*)\n</span><span'
    failures = iter(re.findall(failure_regex, stdio, re.DOTALL)).next()
    if not failures:
        return

    comments = '\n'.join([' ' * 4 + line for line in failures.split('\n')])
    test_names = parse_log(failures)
    if not test_names:
        return

    known_fails = get_known_intermittents(api, test_names)
    if known_fails:
        suffix = ('The following issues exist for tests with known '
                  'intermittent failures:\n - ') + \
                  ' - '.join(map(lambda num: '#%s\n' % num, known_fails))
    else:
        suffix = ("Sorry, these test failures don't match any known "
                  "intermittent failures.\n :disappointed_relieved:")

    api.post_comment(comments + '\n\n' + suffix)


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
