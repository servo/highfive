#!/usr/bin/env python

import base64
import urllib, urllib2
import cgi
import cgitb
try:
    import simplejson as json
except:
    import json
import random
import re
import sys
import ConfigParser
from StringIO import StringIO
import gzip

class APIProvider:
    def __init__(self, payload, user):
        (owner, repo, issue) = extract_globals_from_payload(payload)
        self.owner = owner
        self.repo = repo
        self.issue = issue
        self.user = user

    def is_new_contributor(self, username):
        raise NotImplementedError

    def post_comment(self, body):
        raise NotImplementedError

    def add_label(self, label):
        raise NotImplementedError

    def remove_label(self, label):
        raise NotImplementedError

    def get_labels(self):
        raise NotImplementedError

    def get_diff(self):
        return NotImplementedError

    def set_assignee(self, assignee):
        raise NotImplementedError


class GithubAPIProvider(APIProvider):
    contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=400"
    post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"
    collaborators_url = "https://api.github.com/repos/%s/%s/collaborators"
    issue_url = "https://api.github.com/repos/%s/%s/issues/%s"
    get_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
    add_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
    remove_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels/%s"

    def __init__(self, payload, user, token):
        APIProvider.__init__(self, payload, user)
        self.token = token
        if "pull_request" in payload:
            self.diff_url = payload["pull_request"]["diff_url"]

    def api_req(self, method, url, data=None, media_type=None):
        data = None if not data else json.dumps(data)
        headers = {} if not data else {'Content-Type': 'application/json'}
        req = urllib2.Request(url, data, headers)
        req.get_method = lambda: method
        if token:
            base64string = base64.standard_b64encode('%s:%s' % (self.user, self.token)).replace('\n', '')
            req.add_header("Authorization", "Basic %s" % base64string)

        if media_type:
            req.add_header("Accept", media_type)
        f = urllib2.urlopen(req)
        header = f.info()
        if header.get('Content-Encoding') == 'gzip':
            buf = StringIO(f.read())
            f = gzip.GzipFile(fileobj=buf)
        return { "header": header, "body": f.read() }

    # This function is adapted from https://github.com/kennethreitz/requests/blob/209a871b638f85e2c61966f82e547377ed4260d9/requests/utils.py#L562
    # Licensed under Apache 2.0: http://www.apache.org/licenses/LICENSE-2.0
    def parse_header_links(self, value):
        if not value:
            return None

        links = {}
        replace_chars = " '\""
        for val in value.split(","):
            try:
                url, params = val.split(";", 1)
            except ValueError:
                url, params = val, ''

            url = url.strip("<> '\"")

            for param in params.split(";"):
                try:
                    key, value = param.split("=")
                except ValueError:
                    break
                key = key.strip(replace_chars)
                if key == 'rel':
                    links[value.strip(replace_chars)] = url

        return links

    def is_new_contributor(self, username):
        url = self.contributors_url % (self.owner, self.repo)
        # iterate through the pages to try and find the contributor
        while True:
            stats_raw = self.api_req("GET", url)
            stats = json.loads(stats_raw['body'])
            links = self.parse_header_links(stats_raw['header'].get('Link'))

            for contributor in stats:
                if contributor['login'] == username:
                    return False

            if not links or 'next' not in links:
                return True
            url = links['next']

    def post_comment(self, body):
        try:
            result = self.api_req("POST", self.post_comment_url % (self.owner, self.repo, self.issue),
                                  {"body": body})
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e

    def add_label(self, label):
        try:
            result = self.api_req("POST", self.add_label_url % (self.owner, self.repo, self.issue),
                                  [label])
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e

    def remove_label(self, label):
        try:
            result = self.api_req("DELETE", self.remove_label_url % (self.owner, self.repo, self.issue, label), {})
        except urllib2.HTTPError, e:
            #if e.code == 201:
            #    pass
            #else:
            #    raise e
            pass

    def get_labels(self):
        try:
            result = self.api_req("GET", self.get_label_url % (self.owner, self.repo, self.issue))
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e
        return map(lambda x: x["name"], json.loads(result['body']))

    def get_diff(self):
        return self.api_req("GET", self.diff_url)['body']

    def set_assignee(self, assignee):
        try:
            result = self.api_req("PATCH", self.issue_url % (self.owner, self.repo, self.issue),
                                  {"assignee": assignee})['body']
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e


# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(commit_msg):
    match = reviewer_re.search(commit_msg)
    if not match:
        return None
    return match.group(1)


welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'

reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")

def extract_globals_from_payload(payload):
    if payload["action"] == "created":
        owner = payload['repository']['owner']['login']
        repo = payload['repository']['name']
        issue = str(payload['issue']['number'])
    else:
        owner = payload['pull_request']['base']['repo']['owner']['login']
        repo = payload['pull_request']['base']['repo']['name']
        issue = str(payload["number"])
    return (owner, repo, issue)


def manage_pr_state(api, payload):
    labels = api.get_labels();

    if payload["action"] in ["synchronize", "opened"]:
        for label in ["S-awaiting-merge", "S-tests-failed", "S-needs-code-changes"]:
            if label in labels:
                api.remove_label(label)
        if not "S-awaiting-review" in labels:
            api.add_label("S-awaiting-review")

    # If mergeable is null, the data wasn't available yet. It would be nice to try to fetch that
    # information again.
    if payload["action"] == "synchronize" and payload['pull_request']['mergeable']:
        if "S-needs-rebase" in labels:
            api.remove_label("S-needs-rebase")


def new_comment(api, payload):
    # We only care about comments in open PRs
    if payload['issue']['state'] != 'open' or 'pull_request' not in payload['issue']:
        return

    commenter = payload['comment']['user']['login']
    # Ignore our own comments.
    if commenter == api.user:
        return

    msg = payload["comment"]["body"]
    reviewer = find_reviewer(msg)
    if reviewer:
        api.set_assignee(reviewer)

    if commenter == 'bors-servo':
        labels = api.get_labels();

        if 'has been approved by' in msg or 'Testing commit' in msg:
            for label in ["S-awaiting-review", "S-needs-rebase", "S-tests-failed",
                          "S-needs-code-changes", "S-needs-squash", "S-awaiting-answer"]:
                if label in labels:
                    api.remove_label(label)
            if not "S-awaiting-merge" in labels:
                api.add_label("S-awaiting-merge")

        elif 'Test failed' in msg:
            api.remove_label("S-awaiting-merge")
            api.add_label("S-tests-failed")

        elif 'Please resolve the merge conflicts' in msg:
            api.remove_label("S-awaiting-merge")
            api.add_label("S-needs-rebase")


def new_pr(api, payload):
    manage_pr_state(api, payload)

    author = payload["pull_request"]['user']['login']
    if api.is_new_contributor(author):
        #collaborators = json.load(urllib2.urlopen(collaborators_url))
	collaborators = ['jdm', 'larsbergstrom', 'metajack', 'mbrubeck', 'Ms2ger', 'Manishearth', 'glennw', 'pcwalton', 'SimonSapin'] if api.repo == 'servo' and api.owner == 'servo' else ['test_user_selection_ignore_this']
        random.seed()
        to_notify = random.choice(collaborators)
	api.post_comment(welcome_msg % to_notify)

    warn_unsafe = False
    layout_changed = False
    saw_reftest = False
    diff = api.get_diff()
    for line in diff.split('\n'):
        if line.startswith('+') and not line.startswith('+++') and line.find('unsafe') > -1:
            warn_unsafe = True
        if line.startswith('diff --git') and line.find('components/layout/') > -1:
            layout_changed = True
        if line.startswith('diff --git') and line.find('tests/ref') > -1:
            saw_reftest = True
        if line.startswith('diff --git') and line.find('tests/wpt') > -1:
            saw_reftest = True

    warnings = []
    if warn_unsafe:
        warnings += [unsafe_warning_msg]

    if layout_changed:
        if not saw_reftest:
            warnings += [reftest_required_msg]

    if warnings:
        api.post_comment(warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)))


def update_pr(api, payload):
    manage_pr_state(api, payload)


def handle_payload(api, payload):
    if payload["action"] == "opened":
        new_pr(api, payload)
    elif payload["action"] == "synchronize":
        update_pr(api, payload)
    elif payload["action"] == "created":
        new_comment(api, payload)
    else:
        pass

if __name__ == "__main__":
    print "Content-Type: text/html;charset=utf-8"
    print

    cgitb.enable()

    config = ConfigParser.RawConfigParser()
    config.read('./config')
    user = config.get('github', 'user')
    token = config.get('github', 'token')

    post = cgi.FieldStorage()
    payload_raw = post.getfirst("payload",'')
    payload = json.loads(payload_raw)

    handle_payload(GithubAPIProvider(payload, user, token), payload)
