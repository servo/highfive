from __future__ import absolute_import, print_function
from copy import deepcopy

import json
import os
import sys
import traceback

import eventhandler
from json_cleanup import JsonCleaner
from newpr import APIProvider, handle_payload


class TestAPIProvider(APIProvider):
    def __init__(self, payload, user, new_contributor, labels, assignee,
                 diff="", pull_request=""):
        super(TestAPIProvider, self).__init__(payload, user)
        self.new_contributor = new_contributor
        self.comments_posted = []
        self.labels = labels
        self.assignee = assignee
        self.diff = diff
        self.pull_request = pull_request
        self.repo = str(self.repo)      # workaround for testing

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


def create_test(filename, initial, expected,
                payload_wrapper, to_clean, clean_dict):
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
        'wrapper': payload_wrapper,
        'clean': to_clean,
        'dict': clean_dict,
    }


def run_tests(tests, warn=True, overwrite=False):
    failed, dirty = 0, 0
    for handler, test in tests:
        eventhandler.reset_test_state()

        try:
            initial, expected, = test['initial'], test['expected']
            wrapper = test['wrapper']
            payload = wrapper.json['payload']
            api = TestAPIProvider(payload,
                                  'highfive',
                                  initial['new_contributor'],
                                  initial['labels'],
                                  initial['assignee'],
                                  initial['diff'],
                                  initial['pull_request'])
            handle_payload(api, payload, [handler])

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

            # If this is the last test in the file, then it's time for cleanup
            if test['clean']:
                cleaned = wrapper.clean(warn)

                if wrapper.unused and not overwrite:
                    error = '\033[91m%s\033[0m: The file has %s unused nodes'
                    print(error % (test['filename'], wrapper.unused))
                    dirty += 1

                if overwrite:   # useful for cleaning up the tests locally
                    clean_dict = test['dict']
                    clean_dict['payload'] = cleaned['payload']
                    with open(test['filename'], 'w') as fd:
                        json.dump(clean_dict, fd, indent=2)
                    error = '\033[91m%s\033[0m: Rewrote the JSON file'
                    print(error % test['filename'])

        except AssertionError as error:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)      # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            error_template = '\033[91m{}\033[0m: An error occurred on ' + \
                             'line {} in statement {}'
            print(error_template.format(test['filename'], line, text))
            print(error)
            failed += 1

    return failed, dirty


def register_tests(path):
    tests_location = os.path.join(os.path.dirname(path), 'tests')
    if not os.path.isdir(tests_location):
        return

    tests = [os.path.join(tests_location, f)
             for f in os.listdir(tests_location)
             if f.endswith('.json')]

    for testfile in tests:
        with open(testfile) as f:
            contents = json.load(f)

            # backup the initial/expected values so that we can restore later
            # (if we plan to fix the JSON files)
            clean_dict = {'initial': deepcopy(contents['initial']),
                          'expected': deepcopy(contents['expected'])}

            initial_values = contents['initial']
            expected_values = contents['expected']
            if not isinstance(initial_values, list):
                assert not isinstance(expected_values, list)
                initial_values = [initial_values]
                expected_values = [expected_values]

            wrapper = JsonCleaner({'payload': contents['payload']})
            for i, (initial, expected) in enumerate(zip(initial_values,
                                                        expected_values)):
                min_length = min(len(initial_values), len(expected_values))
                is_last_test = i == min_length - 1
                yield create_test(testfile, initial, expected,
                                  wrapper, is_last_test, clean_dict)


def setup_tests():
    (modules, handlers) = eventhandler.get_handlers()
    tests = []
    for module, handler in zip(modules, handlers):
        for test in register_tests(module[1]):
            tests.append((handler, test))
    return tests


if __name__ == "__main__":
    args = ' '.join(sys.argv)
    overwrite = True if 'write' in args else False

    tests = setup_tests()
    failed, dirty = run_tests(tests, not overwrite, overwrite)

    print('Ran %d tests, %d failed, %d file(s) dirty' %
          (len(tests), failed, dirty))

    if failed or dirty:
        if dirty:
            print('Run `python %s write` to cleanup the dirty files' % args)
        sys.exit(1)
