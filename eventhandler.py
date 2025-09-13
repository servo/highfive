from __future__ import absolute_import
from helpers import linear_search

import importlib.util
import os
import sys

_warnings = []
_payload_actions = {
    'opened': 'on_pr_opened',
    'synchronize': 'on_pr_updated',
    'created': 'on_new_comment',
    'closed': 'on_pr_closed',
    'labeled': 'on_issue_labeled',
    'enqueued': 'on_pr_enqueued',
    'dequeued': 'on_pr_dequeued',
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

    def on_pr_enqueued(self, api, payload):
        pass

    def on_pr_dequeued(self, api, payload):
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
    return _warnings


def get_handlers():
    modules = []
    handlers = []
    possible_handlers = os.listdir('handlers')
    for i in possible_handlers:
        location = os.path.join('handlers', i, "__init__.py")
        abs_location = os.path.join(os.path.dirname(__file__), location)
        spec = importlib.util.spec_from_file_location(i, abs_location)
        if spec is None:
            raise ImportError(
                f"Could not load spec for module '{i}' at: {abs_location}"
            )
        module = importlib.util.module_from_spec(spec)
        sys.modules[i] = module
        spec.loader.exec_module(module)
        handlers.append(module.handler_interface())
        modules.append((module, location))
    return (modules, handlers)
