from errorlogparser import ErrorLogParser
from githubapiprovider import GithubApiProvider
from travisciapiprovider import TravisCiApiProvider


class PayloadHandler():
	def __init__(self, payload):
		self.payload = payload


	def handle_payload(self):
		raise NotImplementedError


class TravisPayloadHandler(PayloadHandler):
    msg_template = "Please fix the error below and push your changes when complete:\n\n" + \
                   "File: {}\nLine Number: {}\nError: {}"

    def __init__(self, payload, github, travis, error_parser):
        PayloadHandler.__init__(self, payload)
        self.travis = travis
        self.github = github
        self.error_parser = error_parser

	def handle_payload(self):
        build_id = int(self.payload["target_url"].split("/")[-1])
        commit_id = self.payload["commit"]["sha"]
        build_id, commit_id, owner, repo = self._extract_globals_from_payload()
        build_data = travis.get_build(build_id)
        log = travis.get_log(travis.get_first_job_id(build_data))
        err_data = error_parser.parse_log(log)
        pr_num = travis.get_pull_request_number(build_data)

        for err_datum in err_data:
            err_message = self.msg_template.format(err_datum['file'], err_datum['line'], err_datum['comment'])
            github.post_review_comment(pr_num, commit_id, err_message, err_datum['file'], err_datum['line'])


class GithubPayloadHandler(PayloadHandler):
    welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."
    warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
    unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
    reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'

    def handle_payload(self):
        if self.payload["action"] == "created":
            issue = str(self.payload['issue']['number'])
        else:
            issue = str(self.payload["number"])

        if self.payload["action"] == "opened":
            self.new_pr(github, issue)
        elif self.payload["action"] == "synchronize":
            self.update_pr(github, issue)
        elif self.payload["action"] == "created":
            self.new_comment(github, issue)
        else:
            pass

    def manage_pr_state(self, github, issue):
        labels = github.get_labels(issue);

        if self.payload["action"] in ["synchronize", "opened"]:
            for label in ["S-awaiting-merge", "S-tests-failed", "S-needs-code-changes"]:
                if label in labels:
                    github.remove_label(label, issue)
            if not "S-awaiting-review" in labels:
                github.add_label("S-awaiting-review", issue)

        # If mergeable is null, the data wasn't available yet. It would be nice to try to fetch that
        # information again.
        if self.payload["action"] == "synchronize" and self.payload['pull_request']['mergeable']:
            if "S-needs-rebase" in labels:
                github.remove_label("S-needs-rebase", issue)


    def new_comment(self, github, issue):
        # We only care about comments in open PRs
        if self.payload['issue']['state'] != 'open' or 'pull_request' not in self.payload['issue']:
            return

        commenter = self.payload['comment']['user']['login']
        # Ignore our own comments.
        if commenter == github.user:
            return

        msg = self.payload["comment"]["body"]
        reviewer = self._find_reviewer(msg)
        if reviewer:
            github.set_assignee(reviewer, issue)

        if commenter == 'bors-servo':
            labels = github.get_labels(issue);

            if 'has been approved by' in msg or 'Testing commit' in msg:
                for label in ["S-awaiting-review", "S-needs-rebase", "S-tests-failed",
                              "S-needs-code-changes", "S-needs-squash", "S-awaiting-answer"]:
                    if label in labels:
                        github.remove_label(label, issue)
                if not "S-awaiting-merge" in labels:
                    github.add_label("S-awaiting-merge")

            elif 'Test failed' in msg:
                github.remove_label("S-awaiting-merge", issue),
                github.add_label("S-tests-failed", issue)

            elif 'Please resolve the merge conflicts' in msg:
                github.remove_label("S-awaiting-merge", issue)
                github.add_label("S-needs-rebase", issue)


    def new_pr(self, github, issue):
        manage_pr_state(github, issue)

        author = self.payload["pull_request"]['user']['login']
        if github.is_new_contributor(author):
            #collaborators = json.load(urllib2.urlopen(collaborators_url))
        collaborators = ['jdm', 'larsbergstrom', 'metajack', 'mbrubeck', 'Ms2ger', 'Manishearth', 'glennw', 'pcwalton', 'SimonSapin'] if github.repo == 'servo' and github.owner == 'servo' else ['test_user_selection_ignore_this']
            random.seed()
            to_notify = random.choice(collaborators)
        github.post_comment(self.welcome_msg % to_notify, issue)

        warn_unsafe = False
        layout_changed = False
        saw_reftest = False
        diff = github.get_diff(self.payload["pull_request"]["diff_url"])
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++') and line.find('unsafe') > -1:
                warn_unsafe = True
            if line.startswith('diff --git') and line.find('components/layout/') > -1:
                layout_changed = True
            if line.startswith('diff --git') and line.find('tests/ref') > -1:
                saw_reftest = True
            if line.startswith('diff --git') and line.find('tests/wpt') > -1:
                saw_reftest = True

        warnings = []
        if warn_unsafe:
            warnings += [self.unsafe_warning_msg]

        if layout_changed:
            if not saw_reftest:
                warnings += [self.reftest_required_msg]

        if warnings:
            github.post_comment(self.warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), issue)


    def update_pr(self, github, issue):
        self.manage_pr_state(github, issue)


    # If the user specified a reviewer, return the username, otherwise returns None.
    def _find_reviewer(self, commit_msg):
        reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
        match = reviewer_re.search(commit_msg)
        if not match:
            return None
        
        return match.group(1)

