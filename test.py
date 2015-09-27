from errorlogparser import ErrorLogParser, ServoErrorLogParser
from githubapiprovider import APIProvider, GithubApiProvider
from mock import call, Mock, patch
from payloadhandler import PayloadHandler, GithubPayloadHandler, TravisPayloadHandler
from travisciapiprovider import TravisCiApiProvider
import json
import os
import payloadreceiver
import sys
import traceback
import unittest
import urlparse

error_sample = [ 
    {
        "body": "use statement is not in alphabetical order\nexpected: dom::bindings::codegen::Bindings::EventHandlerBinding::EventHandlerNonNull\nfound: dom::bindings::conversions::get_dom_class", 
        "position": 7, 
        "path": "./components/script/dom/eventtarget.rs"
    }, 
    {
        "body": "use statement is not in alphabetical order\nexpected: dom::bindings::codegen::Bindings::EventListenerBinding::EventListener\nfound: dom::bindings::codegen::Bindings::EventHandlerBinding::EventHandlerNonNull", 
        "position": 8, 
        "path": "./components/script/dom/eventtarget.rs"
    }, 
    {
        "body": "use statement is not in alphabetical order\nexpected: dom::bindings::codegen::Bindings::EventTargetBinding::EventTargetMethods\nfound: dom::bindings::codegen::Bindings::EventListenerBinding::EventListener", 
        "position": 9, 
        "path": "./components/script/dom/eventtarget.rs"
    }, 
    {
        "body": "use statement is not in alphabetical order\nexpected: dom::bindings::conversions::get_dom_class\nfound: dom::bindings::codegen::Bindings::EventTargetBinding::EventTargetMethods", 
        "position": 10, 
        "path": "./components/script/dom/eventtarget.rs"
    }, 
    {
        "body": "use statement is not in alphabetical order\nexpected: dom::browsercontext\nfound: dom::eventtarget::EventTargetTypeId", 
        "position": 17, 
        "path": "./components/script/dom/bindings/utils.rs"
    }, 
    {
        "body": "use statement is not in alphabetical order\nexpected: dom::eventtarget::EventTargetTypeId\nfound: dom::browsercontext", 
        "position": 18, 
        "path": "./components/script/dom/bindings/utils.rs"
    }
]


class TestAPIProvider(unittest.TestCase):
    def setUp(self):
        self.api_provider = APIProvider('jdm')


    def test_is_new_contributor(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.is_new_contributor("jdm")


    def test_post_comment(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.post_comment("Nice job!", 3947)


    def test_post_review_comment(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.post_review_comment(1234, "a453b3923e893f0383cd2893f...", "foo/bar/spam/eggs", 3, "Remove extra space")


    def test_add_label(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.add_label("S-awaiting-review", 1234)


    def test_remove_label(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.remove_label("S-awaiting-review", 1234)


    def test_get_labels(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.get_labels(1234)


    def test_get_diff(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.get_diff("https://github.com/servo/servo/pull/1234.diff")


    def test_set_assignee(self):
        with self.assertRaises(NotImplementedError):
            self.api_provider.set_assignee("jdm", 1234)


# TODO - add tests for exception handling
class TestGithubApiProvider(unittest.TestCase):
    class FakeHeader():
            def get(self, something):
                pass

    def setUp(self):
        self.owner = "servo"
        self.repo = "servo"
        self.gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        self.gh_provider.api_req = Mock()

    @patch('githubapiprovider.gzip')
    @patch('githubapiprovider.urllib2')
    @patch('githubapiprovider.base64')
    def test_api_req(self, base64_mock, urllib_mock, gzip_mock):
        class FakeRequest():
            def __init__(self):
                self.headers = {}
                self.get_method = lambda: "Get"


            def add_header(self, key, value):
                self.headers[key] = value


        class FakeHeader():
            def get(self, type):
                return 'gzip'


        class FakeResponse():
            def __init__(self, fakeHeader):
                self.header = fakeHeader


            def info(self):
                return self.header


            def read(self):
                return "content"

        faux_request = FakeRequest()
        base64_mock.standard_b64encode = Mock(return_value="User:Token")
        urllib_mock.Request = Mock(return_value=faux_request)
        urllib_mock.urlopen = Mock(return_value=FakeResponse(FakeHeader()))
        gzip_mock.GzipFile = Mock(return_value=FakeResponse(FakeHeader()))
        gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        gh_provider.api_req("GET", "https://api.github.com/repos/servo/servo/contributors", data={"test":"data"}, media_type="Test Media")
        urllib_mock.Request.assert_called_with("https://api.github.com/repos/servo/servo/contributors", json.dumps({"test":"data"}), {'Content-Type':'application/json'})
        urllib_mock.urlopen.assert_called_with(faux_request)


    def test_parse_header_links(self):
        header_links =  '<https://api.github.com/repos/servo/servo/contributors?page=2>; rel="next", <https://api.github.com/repos/servo/servo/contributors?page=11>; rel="last"'
        expected = {'last': 'https://api.github.com/repos/servo/servo/contributors?page=11', 'next': 'https://api.github.com/repos/servo/servo/contributors?page=2'}
        gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        self.assertEquals(expected, gh_provider.parse_header_links(header_links))
        self.assertEquals(None, gh_provider.parse_header_links(None))


    def test_is_new_contributor(self):
        next_page_url = "https://api.github.com/repos/servo/servo/contributors?page=2"
        calls = [call("GET", GithubApiProvider.contributors_url % (self.owner, self.repo)), call("GET", next_page_url)]

        gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        gh_provider.api_req = Mock(side_effect = [{ "header": self.FakeHeader(), "body": json.dumps([{"login":"Ms2ger"}])}, { "header": self.FakeHeader(), "body": json.dumps([{"login":"jdm"}, {"login":"Ms2ger"}])}] )
        gh_provider.parse_header_links = Mock(side_effect = [{"next": next_page_url}, ""])
        
        self.assertFalse(gh_provider.is_new_contributor("jdm"))

        gh_provider.api_req = Mock(side_effect = [{ "header": self.FakeHeader(), "body": json.dumps([{"login":"Ms2ger"}])}, { "header": self.FakeHeader(), "body": json.dumps([{"login":"jdm"}, {"login":"Ms2ger"}])}] )
        gh_provider.parse_header_links = Mock(side_effect = [{"next": next_page_url}, ""])
        
        self.assertTrue(gh_provider.is_new_contributor("JoshTheGoldfish"))
        
        
        gh_provider.api_req.assert_has_calls(calls)


    def test_post_comment(self):
        body = "Great job!"
        issue_num = 1
        self.gh_provider.post_comment(body, issue_num)
        
        self.gh_provider.api_req.assert_called_with("POST", GithubApiProvider.post_comment_url % (self.owner, self.repo, issue_num), {"body":body})


    def test_post_review_comment(self):
        pr_num = 1
        commit_id = "a453b3923e893f0383cd2893f..."
        path = "./file/path",
        pos = 1
        body = "Revmoe extra newline"
        self.gh_provider.post_review_comment(pr_num, commit_id, path, pos, body)
        
        self.gh_provider.api_req.assert_called_with("POST", GithubApiProvider.review_comment_url % (self.owner, self.repo, pr_num), {"body": body, "commit_id":commit_id, "path":path, "position":pos})


    def test_add_label(self):
        label = "S-awaiting-review"
        issue_num = 1
        self.gh_provider.add_label(label, issue_num)
        
        self.gh_provider.api_req.assert_called_with("POST", GithubApiProvider.add_label_url % (self.owner, self.repo, issue_num), [label])


    def test_remove_label(self):
        label = "S-awaiting-review"
        issue_num = 1
        self.gh_provider.remove_label(label, issue_num)
        
        self.gh_provider.api_req.assert_called_with("DELETE", GithubApiProvider.remove_label_url % (self.owner, self.repo, issue_num, label), {})


    def test_get_labels(self):
        gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        issue_num = 1
        label1 = 'S-awaiting-review'
        label2 = 'C-assigned'
        gh_provider.api_req = Mock(return_value = {"header":"", "body":json.dumps([{'name':label1}, {'name':label2}])})
        
        self.assertEquals([label1, label2], gh_provider.get_labels(issue_num))
        gh_provider.api_req.assert_called_with("GET", GithubApiProvider.get_label_url % (self.owner, self.repo, issue_num))


    def test_get_diff(self):
        gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        diff = "fake diff"
        diff_url = "https://github.com/servo/servo/pull/1.diff"
        gh_provider.api_req = Mock(return_value = {"header":"", "body":diff})
        
        self.assertEquals(diff, gh_provider.get_diff("https://github.com/servo/servo/pull/1.diff"))
        gh_provider.api_req.assert_called_with("GET", diff_url)


    def test_set_assignee(self):
        gh_provider = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", self.owner, self.repo)
        issue_num = 1
        assignee = "jdm"
        gh_provider.api_req = Mock(return_value = {"header":"", "body":assignee})

        self.assertEquals(assignee, gh_provider.set_assignee(assignee, issue_num))
        gh_provider.api_req.assert_called_with("PATCH", GithubApiProvider.issue_url % (self.owner, self.repo, issue_num), {"assignee":assignee})

@patch('travisciapiprovider.urllib.urlopen')
class TestTravisCiApiProvider(unittest.TestCase):
    class FakeFile():
        def __init__(self, contents):
            self.contents = contents


        def read(self):
            return self.contents


    def setUp(self):
        self.travis = TravisCiApiProvider()


    def test_get_build(self, urlopen_mock):
        urlopen_mock.return_value = self.FakeFile(json.dumps({"Something":"here"}))
        self.travis.get_build(1)
        urlopen_mock.assert_called_with(TravisCiApiProvider.build_url.format(build_id=1))


    def test_get_log(self, urlopen_mock):
        job_id = 1
        urlopen_mock.return_value = self.FakeFile(open('resources/single-line-comment.log').read())
        self.travis.get_log({"matrix":[{'id':job_id}]})
        urlopen_mock.assert_called_with(TravisCiApiProvider.log_url.format(job_id=job_id))


    def test_get_pull_request_number(self, urlopen_mock):
        pr_num = 1234
        self.assertEquals(1234, self.travis.get_pull_request_number({"compare_url":"https://github.com/servo/servo/{}".format(pr_num)}))


class TestErrorLogParser(unittest.TestCase):
    def setUp(self):
        self.log_parser = ErrorLogParser()


    def test_parse_log(self):
        with self.assertRaises(NotImplementedError):
            self.log_parser.parse_log("log", "regex")


class TestServoErrorLogParser(unittest.TestCase):
    def setUp(self):
        self.error_parser = ServoErrorLogParser()
        self.multi_log = open('resources/multi-line-comment.log').read()
        self.expected_multi_errors = error_sample
        self.single_log = open('resources/single-line-comment.log').read()
        self.expected_single_errors = [
            {
                'body': 'missing space before {', 
                'position': 49, 
                'path': './components/plugins/lints/sorter.rs'
            }
        ]


    def test_parse_errors(self):
        self.assertEqual(self.expected_multi_errors, list(self.error_parser.parse_log(self.multi_log)))
        self.assertEqual(self.expected_single_errors, list(self.error_parser.parse_log(self.single_log)))


class TestPayloadHandler(unittest.TestCase):
    def setUp(self):
        self.handler = PayloadHandler()


    def test_handle_payload(self):
        with self.assertRaises(NotImplementedError):
            self.handler.handle_payload("payload")


class TestTravisPayloadHandler(unittest.TestCase):    
    def setUp(self):
        class TravisDouble():
            def get_build(self, build_id):
                return 1


            def get_log(self, build_data):
                return open('resources/multi-line-comment.log').read()


            def get_pull_request_number(self, build_data):
                return 1


        class ErrorParserDouble():
            path_key = ServoErrorLogParser.path_key
            body_key = ServoErrorLogParser.body_key
            position_key = ServoErrorLogParser.position_key

            def parse_log(self, log):
                return error_sample


        travis_dbl = TravisDouble()
        error_parser_dbl = ErrorParserDouble()
        self.github = GithubApiProvider("jdm", "a453b3923e893f0383cd2893f...", "servo", "servo")
        self.github.post_review_comment = Mock()
        self.github.get_review_comments = Mock(return_value=json.loads(open('resources/review_comments.json').read()))

        self.payload_handler = TravisPayloadHandler(self.github, travis_dbl, error_parser_dbl)
        

    def test_delete_dict_matches(self):
        subject = [{"body":"Hello","position":1,"path":"/hello"}, {"body":"Goodbye","position":1,"path":"/goodbye"}]
        test = [{"body":"Hello","position":1,"path":"/hello"}]
        expected = [{"body":"Goodbye","position":1,"path":"/goodbye"}]

        self.assertEquals(expected, self.payload_handler._delete_existing_comments(subject, test))


    def test_handle_payload(self):
        payload = json.loads(open('resources/test_travis_payload.json').read())
        self.payload_handler.handle_payload(payload)
        err_msg = TravisPayloadHandler.msg_template
        calls = [ 
            call(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[0]['path'], error_sample[0]['position'], error_sample[0]['body']), error_sample[0]['path'], error_sample[0]['position']),
            call(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[1]['path'], error_sample[1]['position'], error_sample[1]['body']), error_sample[1]['path'], error_sample[1]['position']),
            call(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[2]['path'], error_sample[2]['position'], error_sample[2]['body']), error_sample[2]['path'], error_sample[2]['position']),
            call(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[3]['path'], error_sample[3]['position'], error_sample[3]['body']), error_sample[3]['path'], error_sample[3]['position']),
            call(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[4]['path'], error_sample[4]['position'], error_sample[4]['body']), error_sample[4]['path'], error_sample[4]['position']),
            call(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[5]['path'], error_sample[5]['position'], error_sample[5]['body']), error_sample[5]['path'], error_sample[5]['position']),
        ]

        self.github.post_review_comment.assert_called_with(1, "9b6313fd5ab92de5a3fd9f13f8421a929b2a8ef6", err_msg.format(error_sample[3]['path'], error_sample[3]['position'], error_sample[3]['body']), error_sample[3]['path'], error_sample[3]['position'])


class TestGithubPayloadHandler(unittest.TestCase):
    def setUp(self):
        self.github_user = "jdm"
        self.github = GithubApiProvider(self.github_user, "a453b3923e893f0383cd2893f...", "servo", "servo")
        self.github.remove_label = Mock()
        self.github.add_label = Mock()


    def test_handle_payload(self):
        pl_handler = GithubPayloadHandler(None)
        pl_handler.new_pr = Mock()
        pl_handler.update_pr = Mock()
        pl_handler.new_comment = Mock()

        payload = {"action":"created", "issue":{"number":1}}
        pl_handler.handle_payload(payload)
        pl_handler.new_comment.assert_called_with("1", payload)

        payload = {"action":"opened", "number":"1"}
        pl_handler.handle_payload(payload)
        pl_handler.new_pr.assert_called_with("1", payload)

        payload = {"action":"synchronize", "number":"1"}
        pl_handler.handle_payload(payload)
        pl_handler.new_pr.update_pr("1", payload)

        # should not break
        payload = {"action":"other", "number":"1"}
        pl_handler.handle_payload(payload)


    def test_manage_pr_state(self):
        self.github.get_labels = Mock(return_value=["S-awaiting-merge", "S-tests-failed", "S-needs-code-changes", "S-needs-rebase"])
        pl_handler = GithubPayloadHandler(self.github)
        full_cov_payload = {"action":"synchronize", "pull_request":{"mergeable":True}}
        issue_num = 1
        
        pl_handler.manage_pr_state(issue_num, full_cov_payload)
        self.github.get_labels.assert_called_with(issue_num)
        calls = [ 
            call("S-awaiting-merge", issue_num),
            call("S-tests-failed", issue_num),
            call("S-needs-code-changes", issue_num),
            call("S-needs-rebase", issue_num)
        ]
        self.github.remove_label.assert_has_calls(calls)
        self.github.add_label.assert_called_with("S-awaiting-review", issue_num)

    # Not sure it's worth the effort to cover all branches of manage_pr_state


    def test_new_comment_no_action(self):
        pl_handler = GithubPayloadHandler(self.github)
        pl_handler._find_reviewer = Mock()
        payload = {"issue":{"state":"closed"}}
        issue_num = 1

        pl_handler.new_comment(issue_num, payload)
        pl_handler._find_reviewer.assert_not_called()

        payload = {"issue":{"state":"open","pull_request":1},"comment":{"user":{"login":self.github_user}}}
        pl_handler.new_comment(issue_num, payload)
        pl_handler._find_reviewer.assert_not_called()


    def test_new_comment_approved(self):
        self.github.set_assignee = Mock()
        self.github.get_labels = Mock(return_value=["S-awaiting-review"])
        pl_handler = GithubPayloadHandler(self.github)
        payload = {"issue":{"state":"open","pull_request":1},"comment":{"user":{"login":"bors-servo"},"body":"\br?:@jdm Testing commit"}}
        issue_num = 1

        pl_handler.new_comment(issue_num, payload)
        self.github.set_assignee.assert_called_with("jdm", issue_num)
        self.github.get_labels.assert_called_with(issue_num)
        self.github.remove_label.assert_called_with("S-awaiting-review", issue_num)
        self.github.add_label.assert_called_with("S-awaiting-merge")


    def test_new_comment_failed_test(self):
        self.github.set_assignee = Mock()
        self.github.get_labels = Mock()
        pl_handler = GithubPayloadHandler(self.github)
        payload = {"issue":{"state":"open","pull_request":1},"comment":{"user":{"login":"bors-servo"},"body":"\br?:@jdm Test failed"}}
        issue_num = 1

        pl_handler.new_comment(issue_num, payload)
        self.github.remove_label.assert_called_with("S-awaiting-merge", issue_num)
        self.github.add_label.assert_called_with("S-tests-failed", issue_num)


    def test_new_comment_merge_conflicts(self):
        self.github.set_assignee = Mock()
        self.github.get_labels = Mock()
        pl_handler = GithubPayloadHandler(self.github)
        payload = {"issue":{"state":"open","pull_request":1},"comment":{"user":{"login":"bors-servo"},"body":"\br?:@jdm Please resolve the merge conflicts"}}
        issue_num = 1

        pl_handler.new_comment(issue_num, payload)
        self.github.remove_label.assert_called_with("S-awaiting-merge", issue_num)
        self.github.add_label.assert_called_with("S-needs-rebase", issue_num)


    def test_new_pr_no_msg(self):
        self.github.is_new_contributor = Mock(return_value=True)
        self.github.post_comment = Mock()
        self.github.get_diff = Mock(return_value="")
        pl_handler = GithubPayloadHandler(self.github)
        pl_handler.manage_pr_state = Mock()
        pl_handler.post_comment = Mock()
        diff_url = "https://github.com/servo/servo/pull/1234.diff"
        payload = {"pull_request":{"user":{"login":"jdm"},"diff_url":diff_url}}
        issue_num = 1
        rand_val = 'jdm'

        with patch('payloadhandler.random.choice', return_value=rand_val) as mock_random:
            pl_handler.new_pr(issue_num, payload)
            pl_handler.manage_pr_state.assert_called_with(issue_num, payload)
            self.github.post_comment.assert_called_with(GithubPayloadHandler.welcome_msg % rand_val, issue_num)
            self.github.get_diff.assert_called_with(diff_url)


    def test_new_pr_unsafe_msg(self):
        self.github.is_new_contributor = Mock(return_value=False)
        self.github.post_comment = Mock()
        self.github.get_diff = Mock(return_value=open('resources/unsafe.diff').read())
        pl_handler = GithubPayloadHandler(self.github)
        pl_handler.manage_pr_state = Mock()
        pl_handler.post_comment = Mock()
        payload = {"pull_request":{"user":{"login":"jdm"},"diff_url":"https://github.com/servo/servo/pull/1234.diff"}}
        issue_num = 1

        pl_handler.new_pr(issue_num, payload)
        self.github.post_comment.assert_called_with(GithubPayloadHandler.warning_summary % '* ' + GithubPayloadHandler.unsafe_warning_msg, issue_num)


    def test_new_pr_needs_reftest(self):
        self.github.is_new_contributor = Mock(return_value=False)
        self.github.post_comment = Mock()
        self.github.get_diff = Mock(return_value=open('resources/needs_reftest.diff').read())
        pl_handler = GithubPayloadHandler(self.github)
        pl_handler.manage_pr_state = Mock()
        pl_handler.post_comment = Mock()
        payload = {"pull_request":{"user":{"login":"jdm"},"diff_url":"https://github.com/servo/servo/pull/1234.diff"}}
        issue_num = 1

        pl_handler.new_pr(issue_num, payload)
        self.github.post_comment.assert_called_with(GithubPayloadHandler.warning_summary % '* ' + GithubPayloadHandler.reftest_required_msg, issue_num)


    def test_update_pr(self):
        pl_handler = GithubPayloadHandler(self.github)
        pl_handler.manage_pr_state = Mock()
        issue_num = 1
        payload = {"payload"}

        pl_handler.update_pr(issue_num, payload)
        pl_handler.manage_pr_state.assert_called_with(issue_num, payload)


class TestPayloadReceiver(unittest.TestCase):
    def setUp(self):
        self.github_created_payload = json.loads(open('resources/test_post_retry.json').read())
        self.github_other_payload = json.loads(open('resources/test_new_pr.json').read())
        self.travis_payload = json.loads(open('resources/test_travis_payload.json').read())


    def test_extract_globals_from_payload(self):
        self.assertEqual(("servo", "servo"), payloadreceiver.extract_globals_from_payload(self.github_created_payload))
        self.assertEqual(("servo", "servo"), payloadreceiver.extract_globals_from_payload(self.github_other_payload))
        self.assertEqual(("servo", "servo"), payloadreceiver.extract_globals_from_payload(self.travis_payload))


if __name__ == "__main__":
    unittest.main()