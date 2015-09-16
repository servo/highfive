from errorlogparser import ErrorLogParser
from githubapiprovider import GithubApiProvider
from mock import patch
from newpr import APIProvider, handle_payload
from payloadhandler import PayloadHandler
from travisciapiprovider import TravisCiApiProvider
import json
import os
import sys
import traceback
import unittest
import urlparse

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

add_test('test_post_retry.json', {'labels': ['S-tests-failed']},
         {'labels': ['S-awaiting-merge']})

add_test('test_post_retry.json', {'labels': ['S-awaiting-merge']},
         {'labels': ['S-awaiting-merge']})

### Mock Setup
def mock_urllib2_urlopen(url):
    parsed_url = urlparse.urlparse(url.get_full_url())
    local_file = os.path.normpath('test-files/{}'.format(parsed_url.path[1:].replace('/', '.')))

    return open(local_file, 'rb')

def setup_mock_urllib2_urlopen(self, module):
    self.patcher = patch('{}.urllib2.urlopen'.format(module), mock_urllib2_urlopen)
    self.patcher.start()


def mock_urllib_urlopen(url):
    parsed_url = urlparse.urlparse(url)
    local_file = os.path.normpath('test-files/{}'.format(parsed_url.path[1:].replace('/', '.')))

    return open(local_file, 'rb')


def setup_mock_urllib_urlopen(self, module):
    self.patcher = patch('{}.urllib.urlopen'.format(module), mock_urllib_urlopen)
    self.patcher.start()


### Tests

### Todo - Remove these tests and use existing GithubAPI Provider Code
class TestGithubApiProvider(unittest.TestCase):
    def setUp(self):
        setup_mock_urllib2_urlopen(self, 'githubapiprovider')
        self.github = GithubApiProvider("lowfive-servo", "some_fake_token")
        
        self.addCleanup(self.patcher.stop)


    def test_login(self):
        self.github.login()
        self.github.login('lowfive-servo', 'some_fake_token')


    def test_post_review_comment_on_pr(self):
        repo = "servo/servo"
        pr_num = 1 
        commit_id = "6dcb09b5b57875f334f61aebed695e2e4193db5e"
        message = "Great stuff"
        file_path = "file1.txt" 
        line = 1

        self.github.post_review_comment_on_pr(repo, pr_num, commit_id, message, file_path, line)


class TestTravisCiApiProvider(unittest.TestCase):
    def setUp(self):
        setup_mock_urllib_urlopen(self, 'travisciapiprovider')
        self.travis = TravisCiApiProvider()

        self.build_data = self.travis.get_build(1)

        self.addCleanup(self.patcher.stop)


    # These tests are weak
    def test_get_build(self):
        self.assertIn('matrix', self.travis.get_build(1))


    def test_get_log(self):
        self.travis.get_log(self.build_data)


    def test_get_pull_request_number(self):
        build_data = self.travis.get_build(1)

        self.assertEqual(self.travis.get_pull_request_number(build_data), 7601)


class TestErrorLogParser(unittest.TestCase):
    def setUp(self):
        self.log_parser = ErrorLogParser()


    def test_parse_log(self):
        with self.assertRaises(NotImplementedError):
            self.log_parser.parse_log("log", "regex")


class TestPayloadError(unittest.TestCase):
    def setUp(self):
        payload = \
        {
            "target_url": "https://travis-ci.org/servo/servo/builds/74856035",
            "name": "servo/servo",
            "commit": {
                "sha": "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6"
            }
        }

        self.payload_handler = PayloadHandler(payload)


    def test_get_build_id(self):
        self.assertEqual(self.payload_handler.get_build_id(), 74856035)


    def test_get_commit_id(self):
        self.assertEqual(self.payload_handler.get_commit_id(), "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6")


    def test_get_repo_name(self):
        self.assertEqual(self.payload_handler.get_repo_name(), 'servo/servo')


    def test_handle_payload(self):
        with self.assertRaises(NotImplementedError):
            self.payload_handler.handle_payload()

class TestServoErrorLogParser(unittest.TestCase):
    def setUp(self):
        self.error_parser = run.ServoErrorLogParser()
        self.multi_log = open('test-files/multi-line-comment.log').read()
        self.expected_multi_errors = \
        [
            {
                "comment": "use statement is not in alphabetical order\n\texpected: dom::bindings::codegen::Bindings::EventHandlerBinding::EventHandlerNonNull\n\tfound: dom::bindings::conversions::get_dom_class", 
                "line": "7", 
                "file": "./components/script/dom/eventtarget.rs"
            }, 
            {
                "comment": "use statement is not in alphabetical order\n\texpected: dom::bindings::codegen::Bindings::EventListenerBinding::EventListener\n\tfound: dom::bindings::codegen::Bindings::EventHandlerBinding::EventHandlerNonNull", 
                "line": "8", 
                "file": "./components/script/dom/eventtarget.rs"
            }, 
            {
                "comment": "use statement is not in alphabetical order\n\texpected: dom::bindings::codegen::Bindings::EventTargetBinding::EventTargetMethods\n\tfound: dom::bindings::codegen::Bindings::EventListenerBinding::EventListener", 
                "line": "9", 
                "file": "./components/script/dom/eventtarget.rs"
            }, 
            {
                "comment": "use statement is not in alphabetical order\n\texpected: dom::bindings::conversions::get_dom_class\n\tfound: dom::bindings::codegen::Bindings::EventTargetBinding::EventTargetMethods", 
                "line": "10", 
                "file": "./components/script/dom/eventtarget.rs"
            }, 
            {
                "comment": "use statement is not in alphabetical order\n\texpected: dom::browsercontext\n\tfound: dom::eventtarget::EventTargetTypeId", 
                "line": "17", 
                "file": "./components/script/dom/bindings/utils.rs"
            }, 
            {
                "comment": "use statement is not in alphabetical order\n\texpected: dom::eventtarget::EventTargetTypeId\n\tfound: dom::browsercontext", 
                "line": "18", 
                "file": "./components/script/dom/bindings/utils.rs"
            }
        ]

        self.single_log = open('test-files/single-line-comment.log').read()
        self.expected_single_errors = \
        [
            {
                'comment': 'missing space before {', 
                'line': '49', 
                'file': './components/plugins/lints/sorter.rs'
            }
        ]

    def test_parse_errors(self):
        self.assertEqual(self.expected_multi_errors, list(self.error_parser.parse_log(self.multi_log)))
        self.assertEqual(self.expected_single_errors, list(self.error_parser.parse_log(self.single_log)))

if __name__ == "__main__":
    run_tests(tests)
    unittest.main()

