from eventhandler import EventHandler

NO_MODIFY_CSS_TESTS_MSG = '''This pull request modifies the contents of
'tests/wpt/css-tests/', which are overwriten when the directory is synced
from upstream occasionally.'''

class NoModifyCSSTestsHandler(EventHandler):
    DIR_TO_CHECK = "tests/wpt/css-tests"

    def on_pr_opened(self, api, payload):
        for line in api.get_diff().split('\n'):
            if self.DIR_TO_CHECK in line:
                self.warn(NO_MODIFY_CSS_TESTS_MSG)

handler_interface = NoModifyCSSTestsHandler
