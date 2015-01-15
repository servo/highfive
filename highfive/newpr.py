#!/usr/bin/python

import base64
import urllib, urllib2
import cgi
import cgitb
import json
import random
import sys
import ConfigParser
from StringIO import StringIO
import gzip
import re
import time
import socket
import os

from highfive import irc

# Maximum per page is 100. Sorted by number of commits, so most of the time the
# contributor will happen early,
contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=100"
post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"
collabo_url = "https://api.github.com/repos/%s/%s/collaborators"
issue_url = "https://api.github.com/repos/%s/%s/issues/%s"

welcome_msg = """Thanks for the pull request, and welcome! The Rust team is excited to review your changes, and you should hear from @%s (or someone else) soon.

If any changes to this PR are deemed necessary, please add them as extra commits. This ensures that the reviewer can see what has changed since they last reviewed the code. The way Github handles out-of-date commits, this should also make it reasonably obvious what issues have or haven't been addressed. Large or tricky changes may require several passes of review and changes.

Please see [CONTRIBUTING.md](https://github.com/rust-lang/rust/blob/master/CONTRIBUTING.md) for more information.
"""
warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
submodule_warning_msg = 'These commits modify **submodules**.'
review_msg = 'r? @%s\n\n(rust_highfive has picked a reviewer for you, use r? to override)'

reviewer_re = re.compile("[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
unsafe_re = re.compile("\\bunsafe\\b|#!?\\[unsafe_")
submodule_re = re.compile(".*\+Subproject\scommit\s.*", re.DOTALL|re.MULTILINE)

rustaceans_api_url = "http://www.ncameron.org/rustaceans/user?username={username}"


def _load_json_file(name):
    configs_dir = os.path.join(os.path.dirname(__file__), 'configs')

    with open(os.path.join(configs_dir, name)) as config:
        return json.loads(config.read())

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

def set_assignee(assignee, owner, repo, issue, user, token, author):
    global issue_url
    try:
        result = api_req("PATCH", issue_url % (owner, repo, issue), {"assignee": assignee}, user, token)['body']
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
        else:
            raise e

    if assignee:
        irc_name_of_reviewer = get_irc_nick(assignee)
        if irc_name_of_reviewer:
            client = irc.IrcClient(target="#rust-bots")
            client.send_then_quit("{}: ping to review issue https://www.github.com/{}/{}/pull/{} by {}."
                .format(irc_name_of_reviewer, owner, repo, issue, author))


def get_collaborators(owner, repo, user, token):
    try:
        result = api_req("GET", collabo_url % (owner, repo), None, user, token)['body']
    except urllib2.HTTPError, e:
        if e.code == 201:
            pass
        else:
            raise e
    return [c['login'] for c in json.loads(result)]

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

# Choose a reviewer for the PR
def choose_reviewer(repo, owner, diff, exclude):
    if not (owner == 'rust-lang' or (owner == 'nick29581' and repo == 'highfive')):
        return 'test_user_selection_ignore_this'

    # Get JSON data on reviewers.
    reviewers = _load_json_file(repo + '.json')
    dirs = reviewers.get('dirs', {})
    groups = reviewers['groups']

    # fill in the default groups, ensuring that overwriting is an
    # error.
    global_ = _load_json_file('_global.json')
    for name, people in global_['groups'].iteritems():
        assert name not in groups, "group %s overlaps with _global.json" % name
        groups[name] = people


    most_changed = None
    # If there's directories with specially assigned groups/users
    # inspect the diff to find the directory (under src) with the most
    # additions
    if dirs:
        counts = {}
        cur_dir = None
        for line in diff.split('\n'):
            if line.startswith("diff --git "):
                # update cur_dir
                cur_dir = None
                start = line.find(" b/src/") + len(" b/src/")
                if start == -1:
                    continue
                end = line.find("/", start)
                if end == -1:
                    continue

                cur_dir = line[start:end]

                # A few heuristics to get better reviewers
                if cur_dir.startswith('librustc'):
                    cur_dir = 'librustc'
                if cur_dir == 'test':
                    cur_dir = None
                if cur_dir and cur_dir not in counts:
                    counts[cur_dir] = 0
                continue

            if cur_dir and (not line.startswith('+++')) and line.startswith('+'):
                counts[cur_dir] += 1

        # Find the largest count.
        most_changes = 0
        for dir, changes in counts.iteritems():
            if changes > most_changes:
                most_changes = changes
                most_changed = dir

    # lookup that directory in the json file to find the potential reviewers
    potential = groups['all']
    if most_changed and most_changed in dirs:
        potential.extend(dirs[most_changed])


    # expand the reviewers list by group
    reviewers = []
    seen = {"all"}
    while potential:
        p = potential.pop()
        if p.startswith('@'):
            # remove the '@' prefix from each username
            reviewers.append(p[1:])
        elif p in groups:
            # avoid infinite loops
            assert p not in seen, "group %s refers to itself" % p
            seen.add(p)
            # we allow groups in groups, so they need to be queued to be resolved
            potential.extend(groups[p])

    if exclude in reviewers:
        reviewers.remove(exclude)

    random.seed()
    return random.choice(reviewers)


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

def modifies_submodule(diff):
    if submodule_re.match(diff):
        return True
    return False

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


def new_pr(payload, user, token):
    owner = payload['pull_request']['base']['repo']['owner']['login']
    repo = payload['pull_request']['base']['repo']['name']

    author = payload["pull_request"]['user']['login']
    issue = str(payload["number"])
    diff = api_req("GET", payload["pull_request"]["diff_url"])['body']

    msg = payload["pull_request"]['body']
    reviewer = find_reviewer(msg)
    post_msg = False
    if not reviewer:
        post_msg = True
        diff = api_req("GET", payload["pull_request"]["diff_url"])['body']
        reviewer = choose_reviewer(repo, owner, diff, author)

    set_assignee(reviewer, owner, repo, issue, user, token, author)

    if is_new_contributor(author, owner, repo, user, token):
        post_comment(welcome_msg % reviewer, owner, repo, issue, user, token)
    elif post_msg:
        post_comment(review_msg % reviewer, owner, repo, issue, user, token)

    warnings = []
    # Lets not check for unsafe code for now, it doesn't seem to be very useful and gets a lot of false positives.
    #if modifies_unsafe(diff):
    #    warnings += [unsafe_warning_msg]

    if modifies_submodule(diff):
        warnings.append(submodule_warning_msgs)

    if warnings:
        post_comment(warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), owner, repo, issue, user, token)


def new_comment(payload, user, token):
    # Check the issue is a PR and is open.
    if payload['issue']['state'] != 'open' or 'pull_request' not in payload['issue']:
        return

    commenter = payload['comment']['user']['login']
    # Ignore our own comments.
    if commenter == user:
        return

    owner = payload['repository']['owner']['login']
    repo = payload['repository']['name']

    # Check the commenter is the submitter of the PR or the previous assignee.
    author = payload["issue"]['user']['login']
    if not (author == commenter or (payload['issue']['assignee'] and commenter == payload['issue']['assignee']['login'])):
        # Get collaborators for this repo and check if the commenter is one of them
        if commenter not in get_collaborators(owner, repo, user, token):
            return

    # Check for r? and set the assignee.
    msg = payload["comment"]['body']
    reviewer = find_reviewer(msg)
    if reviewer:
        issue = str(payload['issue']['number'])
        set_assignee(reviewer, owner, repo, issue, user, token, author)


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
    if payload["action"] == "opened":
        new_pr(payload, user, token)
    elif payload["action"] == "created":
        new_comment(payload, user, token)
    else:
        print payload["action"]
        sys.exit(0)
