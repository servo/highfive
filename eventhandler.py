import imp
import os

class EventHandler:
    def on_pr_opened(self, api, payload):
        pass

    def on_pr_updated(self, api, payload):
        pass

    def on_new_comment(self, api, payload):
        pass

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
            modules.append(module)
        finally:
            file.close()
    return (modules, handlers)
