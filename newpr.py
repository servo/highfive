#!/usr/bin/python

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

# Maximum per page is 100. Sorted by number of commits, so most of the time the
# contributor will happen early,
contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=100"
post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"

welcome_msg = "Thanks for the pull request, and welcome! The Rust team is excited to review your changes, and you should hear from @%s (or someone else) soon."
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'


def api_req(method, url, data=None, username=None, token=None, media_type=None):
    data = None if not data else json.dumps(data)
    headers = {} if not data else {'Content-Type': 'application/json'}
    req = urllib2.Request(url, data, headers)
    req.get_method = lambda: method
    if token:
        base64string = base64.standard_b64encode('%s:x-oauth-basic' % (token)).replace('\n', '')
        req.add_header("Authorization", "Basic %s" % base64string)

    if media_type:
        req.add_header("Accept", media_type)
    f = urllib2.urlopen(req)
    header = f.info()
    if header.get('Content-Encoding') == 'gzip':
        buf = StringIO(f.read())
        f = gzip.GzipFile(fileobj=buf)
    body = f.read()
    return { "header": header, "body": body }

def post_comment(body, owner, repo, issue, user, token):
    global post_comment_url
    try:
        result = api_req("POST", post_comment_url % (owner, repo, issue), {"body": body}, user, token)['body']
    except urllib2.HTTPError, e:
        if e.code == 201:
                pass
        else:
            raise e

# This function is adapted from https://github.com/kennethreitz/requests/blob/209a871b638f85e2c61966f82e547377ed4260d9/requests/utils.py#L562
# Licensed under Apache 2.0: http://www.apache.org/licenses/LICENSE-2.0
def parse_header_links(value):
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

def is_new_contributor(username, owner, repo, user, token):
    # iterate through the pages to try and find the contributor
    url = contributors_url % (owner, repo)
    while True:
        print 'looking for contribs on ' + url
        stats_raw = api_req("GET", url, None, user, token)
        stats = json.loads(stats_raw['body'])
        links = parse_header_links(stats_raw['header'].get('Link'))

        for contributor in stats:
            if contributor['login'] == username:
                return False

        if not links or 'next' not in links:
            return True
        url = links['next']



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

owner = payload['pull_request']['base']['repo']['owner']['login']
repo = payload['pull_request']['base']['repo']['name']

author = payload["pull_request"]['user']['login']
issue = str(payload["number"])

if is_new_contributor(author, owner, repo, user, token):
    collaborators = ['brson', 'nikomatsakis', 'pcwalton', 'alexcrichton', 'aturon', 'huonw'] if repo == 'rust' and owner == 'rust-lang' else ['test_user_selection_ignore_this']
    random.seed()
    to_notify = random.choice(collaborators)
    post_comment(welcome_msg % to_notify, owner, repo, issue, user, token)

warn_unsafe = False
diff = api_req("GET", payload["pull_request"]["diff_url"])['body']
for line in diff.split('\n'):
    if line.startswith('+') and not line.startswith('+++') and line.find('unsafe') > -1:
        warn_unsafe = True

warnings = []
if warn_unsafe:
    warnings += [unsafe_warning_msg]

if warnings:
    post_comment(warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), owner, repo, issue, user, token)

