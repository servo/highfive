import base64
import json
import urllib2

class GithubApiProvider():
	host_url = 'https://api.github.com'
	login_url = host_url + '/user'
	review_comment_url = host_url + '/repos/{repo}/pulls/{pr_num}/comments'

	def __init__(self, username, token):
		self.username = username
		self.token = token

	def login(self, username=None, token=None):
		username = None if not username else self.username
		token = None if not token else self.token
		base64string = base64.standard_b64encode('{}:{}'.format(username, token))
		req = urllib2.Request(self.login_url)
		req.add_header('Authorization', 'Basic {}'.format(base64string))

		return json.loads(urllib2.urlopen(req).read())

	def post_review_comment_on_pr(self, repo, pr_num, commit_id, message, file_path, line):
	    data = json.dumps({"body":message,"commit_id":commit_id,"path":file_path,"position":line})

	    req = urllib2.Request(self.review_comment_url.format(repo=repo, pr_num=pr_num), data)

	    return json.loads(urllib2.urlopen(req).read())