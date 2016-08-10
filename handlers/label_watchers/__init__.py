from eventhandler import EventHandler
from helpers import get_people_from_config

import os

LABEL_WATCHERS_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                                          'watchers.ini')


def build_label_message(mentions):
    message = ['cc']
    for watcher in mentions:
        message.append("@{}".format(watcher))

    return ' '.join(message)


class LabelWatchersHandler(EventHandler):
    def on_issue_labeled(self, api, payload):
        new_label = payload['label']['name']
        watchers = get_people_from_config(api, LABEL_WATCHERS_CONFIG_FILE)
        if not watchers:
            return

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
