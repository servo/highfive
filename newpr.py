#!/usr/bin/env python

from __future__ import print_function

from base64 import standard_b64encode
import contextlib
import eventhandler
import urllib2
import cgi
import cgitb
try:
    import simplejson as json
except:
    import json
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

    def get_pull(self):
        raise NotImplementedError

    def get_page_content(self, url):
        raise NotImplementedError


class GithubAPIProvider(APIProvider):
    BASE_URL = "https://api.github.com/repos/"
    contributors_url = BASE_URL + "%s/%s/contributors?per_page=400"
    post_comment_url = BASE_URL + "%s/%s/issues/%s/comments"
    collaborators_url = BASE_URL + "%s/%s/collaborators"
    issue_url = BASE_URL + "%s/%s/issues/%s"
    get_label_url = BASE_URL + "%s/%s/issues/%s/labels"
    add_label_url = BASE_URL + "%s/%s/issues/%s/labels"
    remove_label_url = BASE_URL + "%s/%s/issues/%s/labels/%s"

    def __init__(self, payload, user, token):
        APIProvider.__init__(self, payload, user)
        self.token = token
        self._labels = None
        self._diff = None
        if "pull_request" in payload:
            self.diff_url = payload["pull_request"]["diff_url"]
            self.pull_url = payload["pull_request"]["url"]

    def api_req(self, method, url, data=None, media_type=None):
        data = None if not data else json.dumps(data)
        headers = {} if not data else {'Content-Type': 'application/json'}
        req = urllib2.Request(url, data, headers)
        req.get_method = lambda: method
        if token:
            authorization = '%s:%s' % (self.user, self.token)
            base64string = standard_b64encode(authorization).replace('\n', '')
            req.add_header("Authorization", "Basic %s" % base64string)

        if media_type:
            req.add_header("Accept", media_type)
        f = urllib2.urlopen(req)
        header = f.info()
        if header.get('Content-Encoding') == 'gzip':
            buf = StringIO(f.read())
            f = gzip.GzipFile(fileobj=buf)
        return {"header": header, "body": f.read()}

    # This function is adapted from https://github.com/kennethreitz/requests/blob/209a871b638f85e2c61966f82e547377ed4260d9/requests/utils.py#L562  # noqa
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
        url = self.post_comment_url % (self.owner, self.repo, self.issue)
        try:
            self.api_req("POST", url, {"body": body})
        except urllib2.HTTPError as e:
            if e.code == 201:
                pass
            else:
                raise e

    def add_label(self, label):
        url = self.add_label_url % (self.owner, self.repo, self.issue)
        if self._labels:
            self._labels += [label]
        try:
            self.api_req("POST", url, [label])
        except urllib2.HTTPError as e:
            if e.code == 201:
                pass
            else:
                raise e

    def remove_label(self, label):
        url = self.remove_label_url % (self.owner, self.repo, self.issue,
                                       label)
        if self._labels and label in self._labels:
            self._labels.remove(label)
        try:
            self.api_req("DELETE", url, {})
        except urllib2.HTTPError:
            pass

    def get_labels(self):
        url = self.get_label_url % (self.owner, self.repo, self.issue)
        if self._labels is not None:
            return self._labels
        try:
            result = self.api_req("GET", url)
        except urllib2.HTTPError as e:
            if e.code == 201:
                pass
            else:
                raise e
        self._labels = map(lambda x: x["name"], json.loads(result['body']))
        return self._labels

    def get_diff(self):
        if self._diff:
            return self._diff
        self._diff = self.api_req("GET", self.diff_url)['body']
        return self._diff

    def set_assignee(self, assignee):
        url = self.issue_url % (self.owner, self.repo, self.issue)
        try:
            self.api_req("PATCH", url, {"assignee": assignee})['body']
        except urllib2.HTTPError as e:
            if e.code == 201:
                pass
            else:
                raise e

    def get_pull(self):
        return self.api_req("GET", self.pull_url)["body"]

    def get_page_content(self, url):
        try:
            with contextlib.closing(urllib2.urlopen(url)) as fd:
                return fd.read()
        except urllib2.URLError:
            return None


img = ('<img src="http://www.joshmatthews.net/warning.svg" '
       'alt="warning" height=20>')
warning_header = '{} **Warning** {}'.format(img, img)
warning_summary = warning_header + '\n\n%s'


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


def handle_payload(api, payload):
    (modules, handlers) = eventhandler.get_handlers()
    for handler in handlers:
        handler.handle_payload(api, payload)
    warnings = eventhandler.get_warnings()
    if warnings:
        formatted_warnings = '\n'.join(map(lambda x: '* ' + x, warnings))
        api.post_comment(warning_summary % formatted_warnings)


if __name__ == "__main__":
    print("Content-Type: text/html;charset=utf-8")
    print()

    cgitb.enable()

    config = ConfigParser.RawConfigParser()
    config.read('./config')
    user = config.get('github', 'user')
    token = config.get('github', 'token')

    post = cgi.FieldStorage()
    payload_raw = post.getfirst("payload", '')
    payload = json.loads(payload_raw)

    handle_payload(GithubAPIProvider(payload, user, token), payload)
