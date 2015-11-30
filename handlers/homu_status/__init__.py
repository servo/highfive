from eventhandler import EventHandler

class HomuStatusHandler(EventHandler):
    def on_new_comment(self, api, payload):
        if not self.is_open_pr(payload):
            return

        if payload['comment']['user']['login'] != 'bors-servo':
            return

        labels = api.get_labels();
        msg = payload["comment"]["body"]

        def remove_if_exists(label):
            if label in labels:
                api.remove_label(label)

        if 'has been approved by' in msg or 'Testing commit' in msg:
            for label in ["S-awaiting-review", "S-needs-rebase", "S-tests-failed",
                          "S-needs-code-changes", "S-needs-squash", "S-awaiting-answer"]:
                remove_if_exists(label)
            if not "S-awaiting-merge" in labels:
                api.add_label("S-awaiting-merge")

        elif 'Test failed' in msg:
            remove_if_exists("S-awaiting-merge")
            api.add_label("S-tests-failed")

        elif 'Please resolve the merge conflicts' in msg:
            remove_if_exists("S-awaiting-merge")
            api.add_label("S-needs-rebase")


handler_interface = HomuStatusHandler
