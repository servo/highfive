import imp
import json
import os

_warnings = []
_payload_action = {
    'opened': 'on_pr_opened',
    'synchronize': 'on_pr_updated',
    'created': 'on_new_comment',
    'closed': 'on_pr_closed'
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

    def handle_payload(self, api, payload):
        action = payload['action']
        if action in _payload_action:
            getattr(self, _payload_action[action])(api, payload)

    def warn(self, msg):
        global _warnings
        _warnings += [msg]

    def is_open_pr(self, payload):
        return payload['issue']['state'] == 'open' and 'pull_request' in payload['issue']

    def register_tests(self, path):
        from test import create_test
        tests_location = os.path.join(path, 'tests')
        if not os.path.isdir(tests_location):
            return
        tests = [os.path.join(tests_location, f) for f in os.listdir(tests_location) if f.endswith('.json')]
        for testfile in tests:
            with open(testfile) as f:
                contents = json.load(f)
                if not isinstance(contents['initial'], list):
                    assert not isinstance(contents['expected'], list)
                    contents['initial'] = [contents['initial']]
                    contents['expected'] = [contents['expected']]
                for initial, expected in zip(contents['initial'], contents['expected']):
                    yield create_test(testfile, initial, expected)

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
            module = imp.load_module('handlers.'+i, None, location, ('', '', imp.PKG_DIRECTORY))
            handlers.append(module.handler_interface())
            modules.append((module, location))
        except ImportError:
            pass
    return (modules, handlers)
