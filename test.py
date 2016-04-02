from newpr import APIProvider, handle_payload
import json
import os
import sys
import traceback

class TestAPIProvider(APIProvider):
    def __init__(self, payload, user, new_contributor, labels, assignee, diff="", pull_request=""):
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

def get_payload(filename):
    with open(filename) as f:
        return json.load(f)

def create_test(filename, initial, expected):
    global tests
    initial_values = {'new_contributor': initial.get('new_contributor', False),
                      'labels': initial.get('labels', []),
                      'diff': initial.get('diff', ''),
                      'pull_request': initial.get('pull_request', ''),
                      'assignee': initial.get('assignee', None)}
    return {'filename': filename,
            'initial': initial_values,
            'expected': expected}

def run_tests(tests):
    import eventhandler

    failed = 0
    for test in tests:
        eventhandler.reset_test_state()

        try:
            payload = get_payload(test['filename'])['payload']
            initial = test['initial']
            api = TestAPIProvider(payload, 'highfive', initial['new_contributor'], initial['labels'],
                                  initial['assignee'], initial['diff'], initial['pull_request'])
            handle_payload(api, payload)
            expected = test['expected']
            if 'comments' in expected:
                assert len(api.comments_posted) == expected['comments'], "%d == %d" % (len(api.comments_posted), expected['comments'])
            if 'labels' in expected:
                assert api.labels == expected['labels'], "%s == %s" % (api.labels, expected['labels'])
            if 'assignee' in expected:
                assert api.assignee == expected['assignee'], "%s == %s" % (api.assignee, expected['assignee'])
        except AssertionError, error:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb) # Fixed format
            tb_info = traceback.extract_tb(tb)
            filename, line, func, text = tb_info[-1]
            print('{}: An error occurred on line {} in statement {}'.format(test['filename'], line, text))
            print(error)
            failed += 1

    print 'Ran %d tests, %d failed' % (len(tests), failed)

    if failed:
        sys.exit(1)

def setup_tests():
    import eventhandler
    (modules, handlers) = eventhandler.get_handlers()
    tests = []
    for module, handler in zip(modules, handlers):
        tests.extend(handler.register_tests(module[1]))
    return tests

if __name__ == "__main__":
    tests = setup_tests()
    run_tests(tests)
