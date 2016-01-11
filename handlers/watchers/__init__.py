from eventhandler import EventHandler
from ConfigParser import ConfigParser
import os

WATCHERS_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'watchers.ini')

def get_config():
    config = ConfigParser()
    config.read(WATCHERS_CONFIG_FILE)
    return config

def build_message(mentions):
    message = [ 'Watched files:' ]
    for (watcher, file_names) in mentions.items():
        message.append(" * @{}: {}".format(watcher, ', '.join(file_names)))

    return '\n'.join(message)

class WatchersHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        changed_files = []
        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                changed_files.extend(line.split('diff --git ')[-1].split(' '))

        config = get_config()
        mentions = {}
        for section in config.sections():
            for changed_file in changed_files:
                if section in changed_file:
                    for watcher in config.get(section, "watchers").split(' '):
                        if not watcher in mentions:
                            mentions[watcher] = []
                        mentions[watcher].append(changed_file)

        if not mentions:
            return

        message = build_message(mentions)
        print(message)
        api.post_comment(message)




handler_interface = WatchersHandler
