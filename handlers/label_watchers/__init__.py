from eventhandler import EventHandler
import ConfigParser
import os

LABEL_WATCHERS_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                                          'watchers.ini')


def get_label_config():
    config = ConfigParser.ConfigParser()
    config.read(LABEL_WATCHERS_CONFIG_FILE)
    return config


def build_label_message(mentions):
    message = ['cc']
    for watcher in mentions:
        message.append("@{}".format(watcher))

    return ' '.join(message)


class LabelWatchersHandler(EventHandler):
    def on_issue_labeled(self, api, payload):
        new_label = payload['label']['name']
        config = get_label_config()

        repo = api.owner + '/' + api.repo
        try:
            watchers = config.items(repo)
        except ConfigParser.NoSectionError:
            return  # No watchers

        mentions = []
        creator = None
        if 'issue' in payload:
            creator = payload['issue']['user']['login']
        elif 'pull_request' in payload:
            creator = payload['pull_request']['user']['login']

        for (watcher, watched_labels) in watchers:
            if watcher == payload['sender']['login'] or watcher == creator:
                continue

            watched_labels = watched_labels.split(' ')

            if new_label in watched_labels:
                mentions.append(watcher)

        if not mentions:
            return

        message = build_label_message(mentions)
        api.post_comment(message)

handler_interface = LabelWatchersHandler
