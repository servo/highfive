from StringIO import StringIO
import base64
import gzip
try:
    import simplejson as json
except:
    import json
import urllib2


class APIProvider:
    def __init__(self, user):
        self.user = user


    def is_new_contributor(self, username):
        raise NotImplementedError


    def post_comment(self, body, issue):
        raise NotImplementedError


    def post_review_comment(self, pr_num, commit_id, path, pos, body):
    	raise NotImplementedError


    def add_label(self, label, issue):
        raise NotImplementedError


    def remove_label(self, label, issue):
        raise NotImplementedError


    def get_labels(self, issue):
        raise NotImplementedError


    def get_diff(self, url):
        raise NotImplementedError


    def set_assignee(self, assignee, issue):
        raise NotImplementedError


class GithubApiProvider(APIProvider):
    contributors_url = "https://api.github.com/repos/%s/%s/contributors?per_page=400"
    post_comment_url = "https://api.github.com/repos/%s/%s/issues/%s/comments"
    review_comment_url = "https://api.github.com/repos/%s/%s/pulls/%s/comments"
    collaborators_url = "https://api.github.com/repos/%s/%s/collaborators"
    issue_url = "https://api.github.com/repos/%s/%s/issues/%s"
    get_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
    add_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels"
    remove_label_url = "https://api.github.com/repos/%s/%s/issues/%s/labels/%s"

    def __init__(self, user, token, owner, repo):
        APIProvider.__init__(self, user)
        self.token = token

        self.owner = owner
        self.repo = repo

    def api_req(self, method, url, data=None, media_type=None):
        data = None if not data else json.dumps(data)
        headers = {} if not data else {'Content-Type': 'application/json'}
        req = urllib2.Request(url, data, headers)
        req.get_method = lambda: method
        if self.token:
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


    def post_comment(self, body, issue):
        try:
            result = self.api_req("POST", self.post_comment_url % (self.owner, self.repo, issue),
                                  {"body": body})
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e


    def post_review_comment(self, pr_num, commit_id, path, pos, body):
        try:
            result = self.api_req("POST", self.review_comment_url % (self.owner, self.repo, pr_num),
        						  {"body": body, "commit_id":commit_id, "path":path, "position":pos})
        except urllib2.HTTPError, e:
        	if e.code == 201:
        		pass
        	else:
        		raise e


    def get_review_comments(self, pr_num):
        try:
            result = self.api_req("GET", self.review_comment_url % (self.owner, self.repo, pr_num))

            return json.loads(result['body'])
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e


    def add_label(self, label, issue):
        try:
            result = self.api_req("POST", self.add_label_url % (self.owner, self.repo, issue),
                                  [label])
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e


    def remove_label(self, label, issue):
        try:
            result = self.api_req("DELETE", self.remove_label_url % (self.owner, self.repo, issue, label), {})
        except urllib2.HTTPError, e:
            #if e.code == 201:
            #    pass
            #else:
            #    raise e
            pass


    def get_labels(self, issue):
        try:
            result = self.api_req("GET", self.get_label_url % (self.owner, self.repo, issue))
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e
        return map(lambda x: x["name"], json.loads(result['body']))


    def get_diff(self, diff_url):
        return self.api_req("GET", diff_url)['body']


    def set_assignee(self, assignee, issue):
        try:
            result = self.api_req("PATCH", self.issue_url % (self.owner, self.repo, issue),
                                  {"assignee": assignee})

            return result['body']
        except urllib2.HTTPError, e:
            if e.code == 201:
                pass
            else:
                raise e