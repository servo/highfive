from eventhandler import EventHandler

NON_INI_MSG = 'This pull request adds {0} without the .ini \
file extension to {1}. Please consider removing {2}!'

class NonINIWPTMetaFileHandler(EventHandler):
    TEST_DIRS_TO_CHECK = (
        'wpt/metadata',
        'wpt/mozilla/meta',
    )

    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        test_dirs_with_offending_files = set()

        for line in diff.split('\n'):
            for directory in self.TEST_DIRS_TO_CHECK:
                if 'tests/{0}'.format(directory) in line and ('.' in line and '.ini' not in line):
                    test_dirs_with_offending_files.add('tests/{0}'.format(directory))

        if test_dirs_with_offending_files:
            if len(test_dirs_with_offending_files) == 1:
                files = "a file"
                test_dirs_list = test_dirs_with_offending_files.pop()
                remove = "it"
            else:
                files = "files"
                test_dirs_list = '{} and {}'.format(*test_dirs_with_offending_files)
                remove = "them"

            self.warn(NON_INI_MSG.format(files, test_dirs_list, remove))


handler_interface = NonINIWPTMetaFileHandler
