from __future__ import absolute_import

import ConfigParser
import os

COLLABORATORS_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                                         'collaborators.ini')


def get_people_from_config(api, config_abs_path):
    config = ConfigParser.ConfigParser()
    config.read(config_abs_path)
    repo = api.owner + '/' + api.repo

    try:
        return config.items(repo)
    except ConfigParser.NoSectionError:
        return []       # No people


def get_collaborators(api):
    config_items = get_people_from_config(api, COLLABORATORS_CONFIG_FILE)
    return [username for (username, _) in config_items]


def is_addition(diff_line):
    """
    Checks if a line from a unified diff is an addition.
    """
    return diff_line.startswith('+') and not diff_line.startswith('+++')
