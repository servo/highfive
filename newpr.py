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

contributors_url = "https://api.github.com/repos/mozilla/servo/stats/contributors"
collaborators_url = "https://api.github.com/repos/mozilla/servo/collaborators"
post_comment_url = "https://api.github.com/repos/mozilla/servo/issues/%s/comments"

welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."

def api_req(method, url, data, username, token):
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

stats_raw = api_req("GET", contributors_url, None, user, token)
stats = json.loads(stats_raw)

author = payload["pull_request"]['user']['login']
issue = str(payload["number"])

if is_new_contributor(author, stats):
        #collaborators = json.load(urllib2.urlopen(collaborators_url))
	collaborators = ['jdm', 'lbergstrom', 'metajack', 'SimonSapin', 'kmc']
        random.seed()
        to_notify = random.choice(collaborators)
        data = {'body': welcome_msg % to_notify}
	result = api_req("POST", post_comment_url % issue, data, user, token)

