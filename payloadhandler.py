import random
import re
from copy import copy
from errorlogparser import ServoErrorLogParser


class PayloadHandler():
    def handle_payload(self, payload):
        raise NotImplementedError


class TravisPayloadHandler(PayloadHandler):
    msg_template = "Please fix the following error:\n\n**File:** {}\n**Line Number:** {}\n**Error:** {}"

    def __init__(self, github, travis, error_parser):
        self.travis = travis
        self.github = github
        self.error_parser = error_parser

    def handle_payload(self, payload):
        commit_id = self._get_commit_id(payload)
        build_data = self.travis.get_build(self._get_build_id(payload))
        log = self.travis.get_log(build_data)
        err_data = self.error_parser.parse_log(log)
        pr_num = self.travis.get_pull_request_number(build_data)

        existing_comments = [self._build_existing_comment_dict(comment) for comment in self.github.get_review_comments(pr_num)]
        new_comments = [self._build_review_comment_dict(err_datum) for err_datum in err_data]

        comments_to_post = self._delete_existing_comments(new_comments, existing_comments)

        for comment in comments_to_post:
            self.github.post_review_comment(pr_num, commit_id, comment[self.error_parser.body_key], comment[self.error_parser.path_key], comment[self.error_parser.position_key])

    def _build_review_comment_dict(self, err_datum):
        new_datum = err_datum.copy()
        new_datum[self.error_parser.body_key] = self.msg_template.format(err_datum[self.error_parser.path_key], err_datum[self.error_parser.position_key], err_datum[self.error_parser.body_key])

        return new_datum

    def _build_existing_comment_dict(self, comment):
        new_comment = {}

        new_comment[self.error_parser.body_key] = comment[self.error_parser.body_key]
        new_comment[self.error_parser.path_key] = comment[self.error_parser.path_key]
        new_comment[self.error_parser.position_key] = comment[self.error_parser.position_key]

        return new_comment

    def _delete_existing_comments(self, new, existing):
        new_copy = copy(new)
        to_delete = []

        for subject in reversed(new):
            for comment in existing:
                if subject[self.error_parser.body_key] == comment[self.error_parser.body_key] and \
                   subject[self.error_parser.path_key] == comment[self.error_parser.path_key] and \
                   subject[self.error_parser.position_key] == comment[self.error_parser.position_key]:
                    
                    new_copy.remove(subject)
                    break

        return new_copy


    def _get_build_id(self, payload):
        return int(payload["target_url"].split("/")[-1])

    def _get_commit_id(self, payload):
        return payload["commit"]["sha"]


class GithubPayloadHandler(PayloadHandler):
    welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."
    warning_summary = '<img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20> **Warning** <img src="http://www.joshmatthews.net/warning.svg" alt="warning" height=20>\n\n%s'
    unsafe_warning_msg = 'These commits modify **unsafe code**. Please review it carefully!'
    reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'

    def __init__(self, github):
        self.github = github

    def handle_payload(self, payload):
        if payload["action"] == "created":
            issue = str(payload['issue']['number'])
        else:
            issue = str(payload["number"])

        if payload["action"] == "opened":
            self.new_pr(issue, payload)
        elif payload["action"] == "synchronize":
            self.update_pr(issue, payload)
        elif payload["action"] == "created":
            self.new_comment(issue, payload)
        else:
            pass

    def manage_pr_state(self, issue, payload):
        labels = self.github.get_labels(issue);

        if payload["action"] in ["synchronize", "opened"]:
            for label in ["S-awaiting-merge", "S-tests-failed", "S-needs-code-changes"]:
                if label in labels:
                    self.github.remove_label(label, issue)
            if not "S-awaiting-review" in labels:
                self.github.add_label("S-awaiting-review", issue)


        # If mergeable is null, the data wasn't available yet. It would be nice to try to fetch that
        # information again.
        if payload["action"] == "synchronize" and payload['pull_request']['mergeable']:
            if "S-needs-rebase" in labels:
                self.github.remove_label("S-needs-rebase", issue)


    def new_comment(self, issue, payload):
        # We only care about comments in open PRs
        if payload['issue']['state'] != 'open' or 'pull_request' not in payload['issue']:
            return

        commenter = payload['comment']['user']['login']
        # Ignore our own comments.
        if commenter == self.github.user:
            return

        msg = payload["comment"]["body"]
        reviewer = self._find_reviewer(msg)
        if reviewer:
            self.github.set_assignee(reviewer, issue)

        if commenter == 'bors-servo':
            labels = self.github.get_labels(issue)

            if 'has been approved by' in msg or 'Testing commit' in msg:
                for label in ["S-awaiting-review", "S-needs-rebase", "S-tests-failed",
                              "S-needs-code-changes", "S-needs-squash", "S-awaiting-answer"]:
                    if label in labels:
                        self.github.remove_label(label, issue)
                if not "S-awaiting-merge" in labels:
                    self.github.add_label("S-awaiting-merge")

            elif 'Test failed' in msg:
                self.github.remove_label("S-awaiting-merge", issue),
                self.github.add_label("S-tests-failed", issue)

            elif 'Please resolve the merge conflicts' in msg:
                self.github.remove_label("S-awaiting-merge", issue)
                self.github.add_label("S-needs-rebase", issue)


    def new_pr(self, issue, payload):
        self.manage_pr_state(issue, payload)

        author = payload["pull_request"]['user']['login']
        if self.github.is_new_contributor(author):
            #collaborators = json.load(urllib2.urlopen(collaborators_url))
            collaborators = ['jdm', 'larsbergstrom', 'metajack', 'mbrubeck', 'Ms2ger', 'Manishearth', 'glennw', 'pcwalton', 'SimonSapin'] if self.github.repo == 'servo' and self.github.owner == 'servo' else ['test_user_selection_ignore_this']
            random.seed()
            to_notify = random.choice(collaborators)
            self.github.post_comment(self.welcome_msg % to_notify, issue)

        warn_unsafe = False
        layout_changed = False
        saw_reftest = False
        diff = self.github.get_diff(payload["pull_request"]["diff_url"])
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
            self.github.post_comment(self.warning_summary % '\n'.join(map(lambda x: '* ' + x, warnings)), issue)


    def update_pr(self, issue, payload):
        self.manage_pr_state(issue, payload)


    # If the user specified a reviewer, return the username, otherwise returns None.
    def _find_reviewer(self, commit_msg):
        reviewer_re = re.compile("\\b[rR]\?[:\- ]*@([a-zA-Z0-9\-]+)")
        match = reviewer_re.search(commit_msg)
        if not match:
            return None
        
        return match.group(1)

