from __future__ import absolute_import

from eventhandler import EventHandler

NON_INI_MSG = 'This pull request adds {0} without the .ini \
file extension to {1}. Please consider removing {2}!'


class NonINIWPTMetaFileHandler(EventHandler):
    DIRS_TO_CHECK = (
        'tests/wpt/metadata',
        'tests/wpt/mozilla/meta',
    )

    FALSE_POSITIVE_SUBSTRINGS = (
        '.ini',
        'MANIFEST.json',
        'mozilla-sync',
    )

    def _wpt_ini_dirs(self, line):
        if '.' in line and not any(fp in line
                                   for fp in self.FALSE_POSITIVE_SUBSTRINGS):
            return set(directory for directory in self.DIRS_TO_CHECK
                       if directory in line)
        else:
            return set()

    def on_pr_opened(self, api, payload):
        test_dirs_with_offending_files = set()

        for filepath in api.get_changed_files():
            test_dirs_with_offending_files |= self._wpt_ini_dirs(filepath)

        if test_dirs_with_offending_files:
            if len(test_dirs_with_offending_files) == 1:
                files = "a file"
                test_dirs = test_dirs_with_offending_files.pop()
                remove = "it"
            else:
                files = "files"
                test_dirs = '{} and {}'.format(*test_dirs_with_offending_files)
                remove = "them"

            self.warn(NON_INI_MSG.format(files, test_dirs, remove))


handler_interface = NonINIWPTMetaFileHandler
