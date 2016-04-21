from eventhandler import EventHandler
import json
import re
import urllib2

def check_failure_log(api, bors_comment):
    # bors_comment would be something like,
    # ":broken_heart: Test failed - [linux2](http://build.servo.org/builders/linux2/builds/2627)"
    # ... from which we get the relevant build result url
    url = iter(re.findall(r'.*\((.*)\)', bors_comment)).next()
    if not url:
        return

    # substitute and get the new url - http://build.servo.org/json/builders/linux2/builds/2627
    json_url = re.sub(r'(.*)(builders/.*)', r'\1json/\2', url)
    fd = urllib2.urlopen(json_url)
    build_stats = json.loads(fd.read())

    build_log = []
    for step in build_stats['steps']:
        if 'failed' in step['text']:
            build_log = step['logs']
            break

    failed_url = None
    for (name, log_url) in build_log:
        if name == 'stdio':
            failed_url = log_url
            break

    if not failed_url:
        return

    fd = urllib2.urlopen(failed_url)
    stdio = fd.read()
    failures = iter(re.findall(r'.*Tests with unexpected results:\n(.*)\n</span><span',
                               stdio, re.DOTALL)).next()
    if failures:
        comment_body = '\n'.join(map(lambda line: ' ' * 4 + line, failures.split('\n')))
        api.post_comment(comment_body)


class HomuStatusHandler(EventHandler):
    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        if payload['comment']['user']['login'] != 'bors-servo':
            return

        labels = api.get_labels();
        msg = payload["comment"]["body"]

        def remove_if_exists(label):
            if label in labels:
                api.remove_label(label)

        if 'has been approved by' in msg or 'Testing commit' in msg:
            for label in ["S-awaiting-review", "S-needs-rebase", "S-tests-failed",
                          "S-needs-code-changes", "S-needs-squash", "S-awaiting-answer"]:
                remove_if_exists(label)
            if not "S-awaiting-merge" in labels:
                api.add_label("S-awaiting-merge")

        elif 'Test failed' in msg:
            remove_if_exists("S-awaiting-merge")
            api.add_label("S-tests-failed")
            # get the homu build stats url, extract the failed tests and post them!
            check_failure_log(api, msg)

        elif 'Please resolve the merge conflicts' in msg:
            remove_if_exists("S-awaiting-merge")
            api.add_label("S-needs-rebase")


handler_interface = HomuStatusHandler
