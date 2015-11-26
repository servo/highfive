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

def create_test(filename, initial, expected, new_style=False):
    global tests
    initial_values = {'new_contributor': initial.get('new_contributor', False),
                      'labels': initial.get('labels', []),
                      'diff': initial.get('diff', ''),
                      'assignee': initial.get('assignee', None)}
    if new_style:
        expected_values = expected
    else:
        expected_values = {'labels': expected.get('labels', []),
                           'assignee': expected.get('assignee', None),
                           'comments': expected.get('comments', 0)}
    return {'filename': filename,
            'initial': initial_values,
            'expected': expected_values,
            'ignore_missing_expected': new_style}

def run_tests(tests):
    failed = 0
    for test in tests:
        try:
            test_contents = get_payload(test['filename'])
            payload = test_contents['payload'] if 'payload' in test_contents else test_contents
            initial = test['initial']
            api = TestAPIProvider(payload, 'highfive', initial['new_contributor'], initial['labels'],
                                  initial['assignee'], initial['diff'])
            handle_payload(api, payload)
            expected = test['expected']
            ignore_missing = test['ignore_missing_expected']
            if not ignore_missing or 'comments' in expected:
                assert len(api.comments_posted) == expected['comments']
            if not ignore_missing or 'labels' in expected:
                assert api.labels == expected['labels']
            if not ignore_missing or 'assignee' in expected:
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
    if len(possible_tests) > len(test_files):
        print 'Found unused JSON test data: %s' % ', '.join(filter(lambda x: x not in test_files, possible_tests))
        sys.exit(1)
    print 'Ran %d tests, %d failed' % (len(tests), failed)

    if failed:
        sys.exit(1)

def setup_tests():
    import eventhandler
    (modules, handlers) = eventhandler.get_handlers()
    tests = []
    for module, handler in zip(modules, handlers):
        tests.extend(handler.register_tests(module[1]))

    tests += [
        create_test('test_new_pr.json', {'diff': "+ unsafe fn foo()"},
                    {'labels': ['S-awaiting-review'], 'comments': 1}),

        create_test('test_new_pr.json', {'diff': "diff --git components/layout/"},
                    {'labels': ['S-awaiting-review'], 'comments': 1}),

        create_test('test_new_pr.json', {'diff': "diff --git components/layout/\ndiff --git tests/wpt"},
                    {'labels': ['S-awaiting-review'], 'comments': 0}),

        create_test('test_new_pr.json', {'new_contributor': True},
                    {'labels': ['S-awaiting-review'], 'comments': 1}),

        create_test('test_ignored_action.json', {}, {}),

        create_test('test_synchronize.json', {'labels': ['S-needs-code-changes', 'S-tests-failed', 'S-awaiting-merge']},
                    {'labels': ['S-awaiting-review']}),

        create_test('test_comment.json', {}, {'assignee': 'jdm'}),

        create_test('test_merge_approved.json', {'labels': ['S-needs-code-changes', 'S-needs-rebase',
                                                            'S-tests-failed', 'S-needs-squash',
                                                            'S-awaiting-review']}, {'labels': ['S-awaiting-merge']}),

        create_test('test_merge_conflict.json', {'labels': ['S-awaiting-merge']},
                    {'labels': ['S-needs-rebase']}),

        create_test('test_tests_failed.json', {'labels': ['S-awaiting-merge']},
                    {'labels': ['S-tests-failed']}),

        create_test('test_post_retry.json', {'labels': ['S-tests-failed']},
                    {'labels': ['S-awaiting-merge']}),

        create_test('test_post_retry.json', {'labels': ['S-awaiting-merge']},
                    {'labels': ['S-awaiting-merge']})
    ]
    return tests

if __name__ == "__main__":
    tests = setup_tests()
    run_tests(tests)
