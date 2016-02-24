from eventhandler import EventHandler
import random

welcome_msg = "Thanks for the pull request, and welcome! The Servo team is excited to review your changes, and you should hear from @%s (or someone else) soon."

class WelcomeHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        author = payload["pull_request"]['user']['login']
        if api.is_new_contributor(author):
            collaborators = get_collaborators(api) or ['test_user_selection_ignore_this']
            random.seed()
            to_notify = random.choice(collaborators)
            api.post_comment(welcome_msg % to_notify)


handler_interface = WelcomeHandler

