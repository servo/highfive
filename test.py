from newpr import APIProvider, handle_payload
import json
import os

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

def test_new_pr():
    payload = get_payload('test_new_pr.json')
    api = TestAPIProvider(payload, 'highfive', False, [], None)
    handle_payload(api, payload)
    assert api.comments_posted == []
    assert api.labels == ['S-awaiting-review']
    assert api.assignee is None

def test_new_pr_unsafe():
    payload = get_payload('test_new_pr.json')
    api = TestAPIProvider(payload, 'highfive', False, [], None, "+ unsafe fn foo()")
    handle_payload(api, payload)
    assert len(api.comments_posted) == 1
    assert api.labels == ['S-awaiting-review']
    assert api.assignee is None

def test_new_pr_layout():
    payload = get_payload('test_new_pr.json')
    api = TestAPIProvider(payload, 'highfive', False, [], None, "diff --git components/layout/")
    handle_payload(api, payload)
    assert len(api.comments_posted) == 1
    assert api.labels == ['S-awaiting-review']
    assert api.assignee is None

def test_new_pr_layout_with_reftest():
    payload = get_payload('test_new_pr.json')
    api = TestAPIProvider(payload, 'highfive', False, [], None, "diff --git components/layout/\ndiff --git tests/wpt")
    handle_payload(api, payload)
    assert len(api.comments_posted) == 1
    assert api.labels == ['S-awaiting-review']
    assert api.assignee is None

def test_new_pr_new_user():
    payload = get_payload('test_new_pr.json')
    api = TestAPIProvider(payload, 'highfive', True, [], None)
    handle_payload(api, payload)
    assert len(api.comments_posted) == 1
    assert api.labels == ['S-awaiting-review']
    assert api.assignee is None

def test_ignored_action():
    payload = get_payload('test_ignored_action.json')
    api = TestAPIProvider(payload, 'highfive', False, [], None)
    handle_payload(api, payload)
    assert api.comments_posted == []
    assert api.labels == []
    assert api.assignee is None

def test_synchronize():
    payload = get_payload('test_synchronize.json')
    api = TestAPIProvider(payload, 'highfive', False, ['S-needs-code-changes', 'S-tests-failed', 'S-awaiting-merge'], None)
    handle_payload(api, payload)
    assert api.comments_posted == []
    assert api.labels == ['S-awaiting-review']
    assert api.assignee is None

def test_comment():
    payload = get_payload('test_comment.json')
    api = TestAPIProvider(payload, 'highfive', False, [], None)
    handle_payload(api, payload)
    assert api.comments_posted == []
    assert api.labels == []
    assert api.assignee is 'jdm'

def test_merge_approved():
    payload = get_payload('test_merge_approved.json')
    api = TestAPIProvider(payload, 'highfive', False, ['S-needs-code-changes','S-needs-rebase', 'S-tests-failed', 'S-needs-squash'], None)
    handle_payload(api, payload)
    assert api.comments_posted == []
    assert api.labels == ['S-awaiting-merge']
    assert api.assignee is None

def test_tests_failed():
    payload = get_payload('test_tests_failed.json')
    api = TestAPIProvider(payload, 'highfive', False, ['S-awaiting-merge'], None)
    handle_payload(api, payload)
    assert api.comments_posted == []
    assert api.labels == ['S-tests-failed']
    assert api.assignee is None

test_new_pr()
test_new_pr_unsafe()
test_new_pr_layout()
test_new_pr_new_user()
test_ignored_action()
test_synchronize()
test_comment()
