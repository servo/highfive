from __future__ import absolute_import, print_function

import json
import os
import sys
import traceback

import eventhandler
from newpr import APIProvider, handle_payload


class TestAPIProvider(APIProvider):
    def __init__(self, payload, user, new_contributor, labels, assignee,
                 diff="", pull_request=""):
        APIProvider.__init__(self, payload, user)
        self.new_contributor = new_contributor
        self.comments_posted = []
        self.labels = labels
        self.assignee = assignee
        self.diff = diff
        self.pull_request = pull_request

    def is_new_contributor(self, username):
        return self.new_contributor

    def post_comment(self, body):
        self.comments_posted += [body]

    def add_label(self, label):
        self.labels += [label]

    def remove_label(self, label):
        self.labels.remove(label)

    def get_labels(self):
        return self.labels

    def get_diff(self):
        return self.diff

    def get_pull(self):
        return self.pull_request

    def set_assignee(self, assignee):
        self.assignee = assignee

    def get_page_content(self, path):
        with open(path) as fd:
            return fd.read()


def get_payload(filename):
    with open(filename) as f:
        return json.load(f)


def create_test(filename, initial, expected):
    initial_values = {
        'new_contributor': initial.get('new_contributor', False),
        'labels': initial.get('labels', []),
        'diff': initial.get('diff', ''),
        'pull_request': initial.get('pull_request', ''),
        'assignee': initial.get('assignee', None),
    }
    return {
        'filename': filename,
        'initial': initial_values,
        'expected': expected,
    }


def run_tests(tests):
    failed = 0
    for handler, test in tests:
        eventhandler.reset_test_state()

        try:
            payload = get_payload(test['filename'])['payload']
            initial = test['initial']
            api = TestAPIProvider(payload,
                                  'highfive',
                                  initial['new_contributor'],
                                  initial['labels'],
                                  initial['assignee'],
                                  initial['diff'],
                                  initial['pull_request'])
            handle_payload(api, payload)
            expected = test['expected']
            if 'comments' in expected:
                assert len(api.comments_posted) == expected['comments'], \
                    "%d == %d" % (len(api.comments_posted),
                                  expected['comments'])
            if 'labels' in expected:
                assert api.labels == expected['labels'], \
                    "%s == %s" % (api.labels, expected['labels'])
            if 'assignee' in expected:
                assert api.assignee == expected['assignee'], \
                    "%s == %s" % (api.assignee, expected['assignee'])
        except AssertionError as error:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)  # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            error_template = '{}: An error occurred on line {} in statement {}'
            print(error_template.format(test['filename'], line, text))
            print(error)
            failed += 1

    print('Ran %d tests, %d failed' % (len(tests), failed))

    if failed:
        sys.exit(1)


def register_tests(path):
    tests_location = os.path.join(path, 'tests')
    if not os.path.isdir(tests_location):
        return
    tests = [os.path.join(tests_location, f)
             for f in os.listdir(tests_location)
             if f.endswith('.json')]
    for testfile in tests:
        with open(testfile) as f:
            contents = json.load(f)
            if not isinstance(contents['initial'], list):
                assert not isinstance(contents['expected'], list)
                contents['initial'] = [contents['initial']]
                contents['expected'] = [contents['expected']]
            for initial, expected in zip(contents['initial'],
                                         contents['expected']):
                yield create_test(testfile, initial, expected)


def setup_tests():
    (modules, handlers) = eventhandler.get_handlers()
    tests = []
    for module, handler in zip(modules, handlers):
        for test in register_tests(module[1]):
            tests.append((handler, test))
    return tests


if __name__ == "__main__":
    tests = setup_tests()
    run_tests(tests)
