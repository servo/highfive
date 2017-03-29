from copy import deepcopy
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
        label_list = get_people_from_config(api, LABEL_WATCHERS_CONFIG_FILE)
        if not label_list:
            return

        new_label = payload['label']['name']
        existing_labels = []
        if 'issue' in payload:
            for label in payload['issue']['labels']:
                if new_label != label['name']:
                    existing_labels.append(label['name'])

        creator = None
        sender = payload['sender']['login'].lower()

        if 'issue' in payload:
            creator = payload['issue']['user']['login'].lower()
        elif 'pull_request' in payload:
            creator = payload['pull_request']['user']['login'].lower()

        label_map = dict()
        for watcher, watched_labels in label_list:      # reverse map
            if watcher == sender or watcher == creator:
                continue

            for label in watched_labels.split(' '):
                label_map.setdefault(label, set())
                label_map[label].add(watcher)

        mentions = deepcopy(label_map.get(new_label, set()))
        for label in existing_labels:
            for watcher in label_map.get(label, set()):
                if watcher in mentions:     # avoid cc'ing again
                    mentions.remove(watcher)

        if not mentions:
            return

        message = build_label_message(mentions)
        api.post_comment(message)


handler_interface = LabelWatchersHandler
