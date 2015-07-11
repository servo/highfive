#!/usr/bin/env python

import base64
import urllib, urllib2
import cgi
import cgitb
import simplejson as json
import random
import sys
import ConfigParser
from StringIO import StringIO
import gzip
cgitb.enable()

print "Content-Type: text/html;charset=utf-8"
print

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
    post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"
    try:
        result = api_req("POST", post_comment_url % (owner, repo, issue), {"body": body}, user, token)
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
	else:
            raise e

def add_label(label, owner, repo, issue, user, token):
    add_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
    try:
        result = api_req("POST", add_label_url % (owner, repo, issue), [label], user, token)
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
	else:
            raise e

def remove_label(label, owner, repo, issue, user, token):
    remove_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels/%s"
    try:
        result = api_req("DELETE", remove_label_url % (owner, repo, issue, label), {}, user, token)
    except urllib2.HTTPError, e:
        #if e.code == 201:
        #    pass
	#else:
        #    raise e
        pass

def get_labels(owner, repo, issue, user, token):
    get_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
    try:
        result = api_req("GET", get_label_url % (owner, repo, issue), None, user, token)
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
        else:
            raise e
    return map(lambda x: x["name"], json.loads(result))

def is_new_contributor(username, stats):
    for contributor in stats:
        if contributor['login'] == username:
            return False
    return True

contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=400"
collaborators_url = "https://api.github.com/repos/%s/%s/collaborators"

welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'
smoketest_required_msg = '@%s, please confirm that src/test/html/acid1.html and your favourite wikipedia page still render correctly!'

config = ConfigParser.RawConfigParser()
config.read('./config')
user = config.get('github', 'user')
token = config.get('github', 'token')

post = cgi.FieldStorage()
payload_raw = post.getfirst("payload",'')
payload = json.loads(payload_raw)

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

if payload["action"] == "synchronize" and payload['pull_request']['mergeable']:
    if "S-needs-rebase" in labels:
        remove_label("S-needs-rebase", owner, repo, issue, user, token)

if payload["action"] != "opened":
    sys.exit(0)

stats_raw = api_req("GET", contributors_url % (owner, repo), None, user, token)
stats = json.loads(stats_raw)

author = payload["pull_request"]['user']['login']

if is_new_contributor(author, stats):
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
    if line.startswith('diff --git') and line.find('components/main/layout/') > -1:
        layout_changed = True
    if line.startswith('diff --git') and line.find('src/test/ref') > -1:
        saw_reftest = True

warnings = []
if warn_unsafe:
    warnings += [unsafe_warning_msg]

if layout_changed:
    if not saw_reftest:
        warnings += [reftest_required_msg]
    warnings += [smoketest_required_msg % author]

if warnings:
    post_comment(warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), owner, repo, issue, user, token)
