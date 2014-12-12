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
import re
import time
import socket

cgitb.enable()

# Maximum per page is 100. Sorted by number of commits, so most of the time the
# contributor will happen early,
contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=100"
post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"
issue_url = "https://api.github.com/repos/%s/%s/issues/%s"

welcome_msg = """Thanks for the pull request, and welcome! The Rust team is excited to review your changes, and you should hear from @%s (or someone else) soon.

If any changes to this PR are deemed necessary, please add them as extra commits. This ensures that the reviewer can see what has changed since they last reviewed the code. The way Github handles out-of-date commits, this should also make it reasonably obvious what issues have or haven't been addressed. Large or tricky changes may require several passes of review and changes.

Please see [CONTRIBUTING.md](https://github.com/rust-lang/rust/blob/master/CONTRIBUTING.md) for more information.
"""
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'

reviewer_re = re.compile("[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
unsafe_re = re.compile("\\bunsafe\\b|#!?\\[unsafe_")

rustaceans_api_url = "http://www.ncameron.org/rustaceans/user?username={username}"


class IrcClient(object):
    """ A simple IRC client to send a message and then leave.
    the calls to `time.sleep` are so the socket has time to recognize
    responses from the IRC protocol
    """
    def __init__(self, target, nick="rust-highfive", should_join=False):
        self.target = target
        self.nick = nick
        self.should_join = should_join
        self.ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ircsock.connect(("irc.mozilla.org", 6667))
        self.ircsock.send("USER {0} {0} {0} :alert bot!\r\n".format(self.nick))
        self.ircsock.send("NICK {}\r\n".format(self.nick))
        time.sleep(2)

    def join(self):
        self.ircsock.send("JOIN {}\r\n".format(self.target))

    def send(self, msg):
        start = time.time()
        while True:
            if time.time() - start > 5:
                print("Timeout! EXITING")
                return
            ircmsg = self.ircsock.recv(2048).strip()
            #if ircmsg: print(ircmsg)

            if ircmsg.find(self.nick + " +x") != -1:
                self.ircsock.send("PRIVMSG {} :{}\r\n".format(self.target, msg))
                return

    def quit(self):
        self.ircsock.send("QUIT :bot out\r\n")

    def send_then_quit(self, msg):
        if should_join:
            self.join()
        time.sleep(2)
        self.send(msg)
        time.sleep(3)
        self.quit()

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

def set_assignee(assignee, owner, repo, issue, user, token):
    global issue_url
    try:
        result = api_req("PATCH", issue_url % (owner, repo, issue), {"assignee": assignee}, user, token)['body']
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

# If the user specified a reviewer, return the username, otherwise returns None.
def find_reviewer(commit_msg):
    match = reviewer_re.search(commit_msg)
    if not match:
        return None
    return match.group(1)

#def modifies_unsafe(diff):
#    in_rust_code = False
#    for line in diff.split('\n'):
#        if line.startswith("diff --git "):
#            in_rust_code = line[-3:] == ".rs" and line.find(" b/src/test/") == -1
#            continue
#        if not in_rust_code:
#            continue
#        if (not line.startswith('+') or line.startswith('+++')) and not line.startswith("@@ "):
#            continue
#        if unsafe_re.search(line):
#            return True
#    return False

def get_irc_nick(gh_name):
    """ returns None if the request status code is not 200,
     if the user does not exist on the rustacean database,
     or if the user has no `irc` field associated with their username
    """
    data = urllib2.urlopen(rustaceans_api_url.format(username=gh_name))
    if data.getcode() == 200:
        rustacean_data = json.loads(data.read())
        if rustacean_data:
            return rustacean_data[0].get("irc")
    return None


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
    set_assignee(to_notify, owner, repo, issue, user, token)
else:
    msg = payload["pull_request"]['body']
    reviewer = find_reviewer(msg)
    if reviewer:
        set_assignee(reviewer, owner, repo, issue, user, token)

diff = api_req("GET", payload["pull_request"]["diff_url"])['body']

warnings = []
# Lets not check unsafe code for now, it doesn't seem to be very useful and gets a lot of false positives.
#if modifies_unsafe(diff):
#    warnings += [unsafe_warning_msg]

if warnings:
    post_comment(warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), owner, repo, issue, user, token)

if reviewer:
    irc_name_of_reviewer = get_irc_nick(reviewer)
    if irc_name_of_reviewer:
        client = IrcClient(target="#rust-bots")
        client.send_then_quit("{}: ping to review issue https://www.github.com/rust-lang/rust/pull/{} by {}. Have a nice day!"
            .format(get_irc_nick(reviewer), issue, author))
