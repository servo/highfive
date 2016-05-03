from eventhandler import EventHandler

TEST_REQUIRED_MSG = ('These commits modify {} code, but no tests are modified.'
                     'Please consider adding a test!')


class MissingTestHandler(EventHandler):
    COMPONENT_DIRS_TO_CHECK = ('layout', 'script', 'gfx', 'style', 'net')
    TEST_DIRS_TO_CHECK = ('ref', 'wpt', 'unit')

    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        components_changed = set()

        for line in diff.split('\n'):
            if line.startswith('diff --git'):
                for component in self.COMPONENT_DIRS_TO_CHECK:
                    if 'components/{0}/'.format(component) in line:
                        components_changed.add(component)

                for directory in self.TEST_DIRS_TO_CHECK:
                    if 'tests/{0}'.format(directory) in line:
                        return

        if components_changed:
            # Build a readable list of changed components
            if len(components_changed) == 1:
                components_msg = components_changed.pop()
            elif len(components_changed) == 2:
                components_msg = '{} and {}'.format(*components_changed)
            else:
                components_msg = ', '.join(components_changed)
                components_msg = ", and ".join(components_msg.rsplit(", ", 1))

            self.warn(TEST_REQUIRED_MSG.format(components_msg))


handler_interface = MissingTestHandler
