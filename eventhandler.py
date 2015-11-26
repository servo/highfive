import imp
import json
import os

class EventHandler:
    def on_pr_opened(self, api, payload):
        pass

    def on_pr_updated(self, api, payload):
        pass

    def on_new_comment(self, api, payload):
        pass

    def register_tests(self, path):
        from test import create_test
        tests_location = os.path.join(path, 'tests')
        if not os.path.isdir(tests_location):
            return
        tests = [os.path.join(tests_location, f) for f in os.listdir(tests_location) if f.endswith('.json')]
        for testfile in tests:
            with open(testfile) as f:
                contents = json.load(f)
                yield create_test(testfile, contents['initial'], contents['expected'], True)

def get_handlers():
    modules = []
    handlers = []
    possiblehandlers = os.listdir('handlers')
    for i in possiblehandlers:
        location = os.path.join('handlers', i)
        module = '__init__'
        if not os.path.isdir(location) or not module + ".py" in os.listdir(location):
            continue
        try:
            (file, pathname, description) = imp.find_module(module, [location])
            module = imp.load_module(module, file, pathname, description)
            handlers.append(module.handler_interface())
            modules.append((module, location))
        finally:
            file.close()
    return (modules, handlers)
