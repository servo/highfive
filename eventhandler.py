from __future__ import absolute_import
from helpers import linear_search

import imp
import os

_warnings = []
_payload_actions = {
    'opened': 'on_pr_opened',
    'synchronize': 'on_pr_updated',
    'created': 'on_new_comment',
    'closed': 'on_pr_closed',
    'labeled': 'on_issue_labeled'
}

DIFF_HEADER_LINE_START = 'diff --git '


class EventHandler:
    def on_pr_opened(self, api, payload):
        pass

    def on_pr_updated(self, api, payload):
        pass

    def on_new_comment(self, api, payload):
        pass

    def on_pr_closed(self, api, payload):
        pass

    def on_issue_labeled(self, api, payload):
        pass

    def handle_payload(self, api, payload):
        def callback(action):
            getattr(self, _payload_actions[action])(api, payload)
        payload_action = payload['action']
        linear_search(_payload_actions, payload_action, callback)

    def warn(self, msg):
        global _warnings
        _warnings += [msg]

    def is_open_pr(self, payload):
        return (payload['issue']['state'] == 'open' and
                'pull_request' in payload['issue'])


    def get_diff_headers(self, api):
        diff = api.get_diff()
        for line in diff.split('\n'):
            if line.startswith(DIFF_HEADER_LINE_START):
                yield line

    def get_added_lines(self, api):
        diff = api.get_diff()
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                # prefix of one or two pluses (+)
                yield line

    def get_changed_files(self, api):
        changed_files = []
        for line in self.get_diff_headers(api):
            changed_files.extend(line.split(DIFF_HEADER_LINE_START)[-1].split(' '))

        # Remove the `a/` and `b/` parts of paths,
        # And get unique values using `set()`
        return set(f if f.startswith('/') else f[2:] for f in changed_files)


def reset_test_state():
    global _warnings
    _warnings = []


def get_warnings():
    global _warnings
    return _warnings


def get_handlers():
    modules = []
    handlers = []
    possiblehandlers = os.listdir('handlers')
    for i in possiblehandlers:
        location = os.path.join('handlers', i)
        try:
            module = imp.load_module('handlers.' + i, None, location,
                                     ('', '', imp.PKG_DIRECTORY))
            handlers.append(module.handler_interface())
            modules.append((module, location))
        except ImportError:
            pass
    return (modules, handlers)
