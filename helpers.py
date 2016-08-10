from __future__ import absolute_import

import ConfigParser
import os

COLLABORATORS_CONFIG_FILE = os.path.join(os.path.dirname(__file__),
                                         'collaborators.ini')


_test_path_roots = ['a/', 'b/']


def get_people_from_config(api, config_abs_path):
    '''
    Gets the people listed under a particular repo from a config file.
    Note that the names (despite how they're in the file) will always
    be parsed to 'lowercase'.
    '''
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


def normalize_file_path(filepath):
    """
    Strip any leading/training whitespace.
    Remove any test directories from the start of the path
    """
    if filepath is None or filepath.strip() == '':
        return None
    filepath = filepath.strip()
    for prefix in _test_path_roots:
        if filepath.startswith(prefix):
            return filepath[len(prefix):]
    return filepath


def linear_search(sequence, element, callback=lambda thing: thing):
    """
    The 'in' operator also does a linear search over a sequence, but it checks
    for the exact match of the given object, whereas this makes use of '==',
    which calls the '__eq__' magic method, which could've been overridden in
    a custom class (which is the case for our test lint)
    """
    for thing in sequence:
        if element == thing:    # element could have an overridden '__eq__'
            callback(thing)
