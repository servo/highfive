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
