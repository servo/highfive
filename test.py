from newpr import APIProvider, handle_payload
import json
import os
import sys
import traceback

class TestAPIProvider(APIProvider):
    def __init__(self, payload, user, new_contributor, labels, assignee, diff=""):
        APIProvider.__init__(self, payload, user)
        self.new_contributor = new_contributor
        self.comments_posted = []
        self.labels = labels
        self.assignee = assignee
        self.diff = diff

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

    def set_assignee(self, assignee):
        self.assignee = assignee

def get_payload(filename):
    with open(filename) as f:
        return json.load(f)

tests = []
def add_test(filename, initial, expected):
    global tests
    initial_values = {'new_contributor': initial.get('new_contributor', False),
                      'labels': initial.get('labels', []),
                      'diff': initial.get('diff', ''),
                      'assignee': initial.get('assignee', None)}
    expected_values = {'labels': expected.get('labels', []),
                       'assignee': expected.get('assignee', None),
                       'comments': expected.get('comments', 0)}
    tests += [{'filename': filename,
               'initial': initial_values,
               'expected': expected_values}]

def run_tests(tests):
    failed = 0
    for test in tests:
        try:
            payload = get_payload(test['filename'])
            initial = test['initial']
            api = TestAPIProvider(payload, 'highfive', initial['new_contributor'], initial['labels'],
                                  initial['assignee'], initial['diff'])
            handle_payload(api, payload)
            expected = test['expected']
            assert len(api.comments_posted) == expected['comments']
            assert api.labels == expected['labels']
            assert api.assignee == expected['assignee']
        except AssertionError:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb) # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            print('{}: An error occurred on line {} in statement {}'.format(test['filename'], line, text))
            failed += 1

    possible_tests = [f for f in os.listdir('.') if f.endswith('.json')]
    test_files = set([test['filename'] for test in tests])
    if len(possible_tests) != len(test_files):
        print 'Found unused JSON test data: %s' % ', '.join(filter(lambda x: x not in test_files, possible_tests))
        sys.exit(1)
    print 'Ran %d tests, %d failed' % (len(tests), failed)

    if failed:
        sys.exit(1)

add_test('test_new_pr.json', {'new_contributor': True},
         {'labels': ['S-awaiting-review'], 'comments': 1})

add_test('test_new_pr.json', {'diff': "+ unsafe fn foo()"},
         {'labels': ['S-awaiting-review'], 'comments': 1})

add_test('test_new_pr.json', {'diff': "diff --git components/layout/"},
         {'labels': ['S-awaiting-review'], 'comments': 1})

add_test('test_new_pr.json', {'diff': "diff --git components/layout/\ndiff --git tests/wpt"},
         {'labels': ['S-awaiting-review'], 'comments': 0})

add_test('test_new_pr.json', {'new_contributor': True},
         {'labels': ['S-awaiting-review'], 'comments': 1})

add_test('test_ignored_action.json', {}, {})

add_test('test_synchronize.json', {'labels': ['S-needs-code-changes', 'S-tests-failed', 'S-awaiting-merge']},
         {'labels': ['S-awaiting-review']})

add_test('test_comment.json', {}, {'assignee': 'jdm'})

add_test('test_merge_approved.json', {'labels': ['S-needs-code-changes', 'S-needs-rebase',
                                                 'S-tests-failed', 'S-needs-squash',
                                                 'S-awaiting-review']}, {'labels': ['S-awaiting-merge']})

add_test('test_merge_conflict.json', {'labels': ['S-awaiting-merge']},
         {'labels': ['S-needs-rebase']})

add_test('test_tests_failed.json', {'labels': ['S-awaiting-merge']},
         {'labels': ['S-tests-failed']})

run_tests(tests)
