#!/usr/bin/env python

import base64
import urllib, urllib2
import cgi
import cgitb
import simplejson as json
import random
import re
import sys
import ConfigParser
from StringIO import StringIO
import gzip
cgitb.enable()

print "Content-Type: text/html;charset=utf-8"
print

contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=400"
post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"
collaborators_url = "https://api.github.com/repos/%s/%s/collaborators"
issue_url = "https://api.github.com/repos/%s/%s/issues/%s"
get_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
add_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
remove_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels/%s"

def api_req(method, url, data=None, username=None, token=None, media_type=None):
    data = None if not data else json.dumps(data)
    headers = {} if not data else {'Content-Type': 'application/json'}
    req = urllib2.Request(url, data, headers)
    req.get_method = lambda: method
    if token:
        base64string = base64.standard_b64encode('%s:%s' % (username, token)).replace('\n', '')
        req.add_header("Authorization", "Basic %s" % base64string)

    if media_type:
        req.add_header("Accept", media_type)
    f = urllib2.urlopen(req)
    if f.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(f.read())
        f = gzip.GzipFile(fileobj=buf)
    return f.read()

def post_comment(body, owner, repo, issue, user, token):
    global post_comment_url
    try:
        result = api_req("POST", post_comment_url % (owner, repo, issue), {"body": body}, user, token)
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
	else:
            raise e

def add_label(label, owner, repo, issue, user, token):
    global add_label_url
    try:
        result = api_req("POST", add_label_url % (owner, repo, issue), [label], user, token)
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
	else:
            raise e

def remove_label(label, owner, repo, issue, user, token):
    global remove_label_url
    try:
        result = api_req("DELETE", remove_label_url % (owner, repo, issue, label), {}, user, token)
    except urllib2.HTTPError, e:
        #if e.code == 201:
        #    pass
	#else:
        #    raise e
        pass

def get_labels(owner, repo, issue, user, token):
    global get_label_url
    try:
        result = api_req("GET", get_label_url % (owner, repo, issue), None, user, token)
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
        else:
            raise e
    return map(lambda x: x["name"], json.loads(result))

# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(commit_msg):
    match = reviewer_re.search(commit_msg)
    if not match:
        return None
    return match.group(1)


def is_new_contributor(username, owner, repo, user, token):
    # iterate through the pages to try and find the contributor
    url = contributors_url % (owner, repo)
    while True:
        stats_raw = api_req("GET", url, None, user, token)
        stats = json.loads(stats_raw['body'])
        links = parse_header_links(stats_raw['header'].get('Link'))

        for contributor in stats:
            if contributor['login'] == username:
                return False

        if not links or 'next' not in links:
            return True
        url = links['next']


def set_assignee(assignee, owner, repo, issue, user, token, author):
    global issue_url
    try:
        result = api_req("PATCH", issue_url % (owner, repo, issue), {"assignee": assignee}, user, token)['body']
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
        else:
            raise e


welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'

reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")

config = ConfigParser.RawConfigParser()
config.read('./config')
user = config.get('github', 'user')
token = config.get('github', 'token')

post = cgi.FieldStorage()
payload_raw = post.getfirst("payload",'')
payload = json.loads(payload_raw)

if payload["action"] == "created":
    owner = payload['repository']['owner']['login']
    repo = payload['repository']['name']
    issue = str(payload['issue']['number'])
else:
    owner = payload['pull_request']['base']['repo']['owner']['login']
    repo = payload['pull_request']['base']['repo']['name']
    issue = str(payload["number"])

labels = get_labels(owner, repo, issue, user, token);

if payload["action"] in ["synchronize", "opened"]:
    for label in ["S-awaiting-merge", "S-tests-failed", "S-needs-code-changes"]:
        if label in labels:
            remove_label(label, owner, repo, issue, user, token)
    if not "S-awaiting-review" in labels:
        add_label("S-awaiting-review", owner, repo, issue, user, token)

# If mergeable is null, the data wasn't available yet. It would be nice to try to fetch that
# information again.
if payload["action"] == "synchronize" and payload['pull_request']['mergeable']:
    if "S-needs-rebase" in labels:
        remove_label("S-needs-rebase", owner, repo, issue, user, token)

if payload["action"] == "created":
    # We only care about comments in open PRs
    if not (payload['issue']['state'] != 'open' or 'pull_request' not in payload['issue']):
        sys.exit(0);

    commenter = payload['comment']['user']['login']
    # Ignore our own comments.
    if commenter == user:
        return

    msg = payload["comment"]["body"]
    reviewer = find_reviewer(msg)
    if reviewer:
        set_assignee(reviewer, owner, repo, issue, user, token, author)

    if commenter == 'bors-servo':
        if 'has been approved by' in msg:
            for label in ["S-needs-rebase", "S-tests-failed", "S-needs-code-changes", "S-needs-squash"]:
                if label in labels:
                    remove_label(label, owner, issue, user, token)
            add_label("S-awaiting-merge", owner, repo, issue, user, token)

        elif 'Test failed' in msg:
            remove_label("S-awaiting-merge", owner, repo, issue, user, token)
            add_label("S-tests-failed", owner, repo, issue, user, token)

if payload["action"] != "opened":
    sys.exit(0)

author = payload["pull_request"]['user']['login']

if is_new_contributor(author, owner, repo, user, token):
        #collaborators = json.load(urllib2.urlopen(collaborators_url))
	collaborators = ['jdm', 'larsbergstrom', 'metajack', 'mbrubeck', 'Ms2ger', 'Manishearth', 'glennw', 'pcwalton', 'SimonSapin'] if repo == 'servo' and owner == 'servo' else ['test_user_selection_ignore_this']
        random.seed()
        to_notify = random.choice(collaborators)
	post_comment(welcome_msg % to_notify, owner, repo, issue, user, token)

warn_unsafe = False
layout_changed = False
saw_reftest = False
diff = api_req("GET", payload["pull_request"]["diff_url"])
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
    post_comment(warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), owner, repo, issue, user, token)
