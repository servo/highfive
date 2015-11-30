from eventhandler import EventHandler

def manage_pr_state(api, payload):
    labels = api.get_labels();

    for label in ["S-awaiting-merge", "S-tests-failed", "S-needs-code-changes"]:
        if label in labels:
            api.remove_label(label)
    if not "S-awaiting-review" in labels:
        api.add_label("S-awaiting-review")

    # If mergeable is null, the data wasn't available yet. It would be nice to try to fetch that
    # information again.
    if payload["action"] == "synchronize" and payload['pull_request']['mergeable']:
        if "S-needs-rebase" in labels:
            api.remove_label("S-needs-rebase")

class StatusUpdateHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        manage_pr_state(api, payload)

    def on_pr_updated(self, api, payload):
        manage_pr_state(api, payload)


handler_interface = StatusUpdateHandler
