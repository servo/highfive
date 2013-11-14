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

def is_new_contributor(username, stats):
    for contributor in stats:
        if contributor['author']['login'] == username:
            return False
    return True

contributors_url = "https://api.github.com/repos/%s/%s/stats/contributors"
collaborators_url = "https://api.github.com/repos/%s/%s/collaborators"
post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"

welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'

def api_req(method, url, data=None, username=None, token=None):
	data = json.dumps(data)
	req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
	req.get_method = lambda: method
	if token:
        	base64string = base64.standard_b64encode('%s:%s' % (username, token)).replace('\n', '')
        	req.add_header("Authorization", "Basic %s" % base64string)

	f = urllib2.urlopen(req)
	if f.info().get('Content-Encoding') == 'gzip':
	    buf = StringIO(f.read())
	    f = gzip.GzipFile(fileobj=buf)
	return f.read()

print "Content-Type: text/html;charset=utf-8"
print

config = ConfigParser.RawConfigParser()
config.read('./config')
user = config.get('github', 'user')
token = config.get('github', 'token')

post = cgi.FieldStorage()
payload_raw = post.getfirst("payload",'')
payload = json.loads(payload_raw)
if payload["action"] != "opened":
	sys.exit(0)

owner = payload['pull_request']['repo']['owner']['login']
repo = payload['pull_request']['repo']['name']
stats_raw = api_req("GET", contributors_url % (owner, repo), None, user, token)
stats = json.loads(stats_raw)

author = payload["pull_request"]['user']['login']
issue = str(payload["number"])

if is_new_contributor(author, stats):
        #collaborators = json.load(urllib2.urlopen(collaborators_url))
	collaborators = ['jdm', 'lbergstrom', 'metajack', 'SimonSapin', 'kmcallister']
        random.seed()
        to_notify = random.choice(collaborators)
        data = {'body': welcome_msg % to_notify}
        result = api_req("POST", post_comment_url % (owner, repo, issue), data, user, token)

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
    warnings.push(unsafe_warning_msg)

if layout_changed and not saw_reftest:
    warnings.push(reftest_required_msg)

if warnings:
    data = {'body': warning_summary % map(lambda x: '* ' + x, warnings).join('\n')}
    result = api_req("POST", post_comment_url % (owner, repo, issue), data, user, token)
