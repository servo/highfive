#!/usr/bin/env python

from errorlogparser import ErrorLogParser
from githubapiprovider import GithubApiProvider
from payloadhandler import PayloadHandler
from StringIO import StringIO
from travisciapiprovider import TravisCiApiProvider
import base64
import cgi
import cgitb
import ConfigParser
import gzip
try:
    import simplejson as json
except:
    import json
import random
import re
import sys
import urllib, urllib2

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
    post_review_comment_url = "https://api.github.com/repos/%s/pulls/%s/comments"
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

    # find a way to get 
    def post_review_comment_on_pr(self, repo, pr_num, commit_id, message, file_path, line):
        try:
            result = self.api_req("POST", self.post_review_comment_url % (self.repo, self.pr_num))
        data = json.dumps({"body":message,"commit_id":commit_id,"path":file_path,"position":line})

        req = urllib2.Request(self.review_comment_url.format(repo=repo, pr_num=pr_num), data)

        return json.loads(urllib2.urlopen(req).read())


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

    if "action" in payload:
        payload_handler = GithubPayloadHandler(payload)
    elif "state" in payload:
        payload_hanlder = TravisPayloadHandler(payload)
        # get TravisCiApiProvider
        # get ErrorParser

    handle_payload(GithubAPIProvider(payload, user, token), payload)
