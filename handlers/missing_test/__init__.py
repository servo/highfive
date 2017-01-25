from __future__ import absolute_import

from eventhandler import EventHandler

TEST_REQUIRED_MSG = ('These commits modify {} code, but no tests are modified.'
                     ' Please consider adding a test!')


class MissingTestHandler(EventHandler):
    COMPONENT_DIRS_TO_CHECK = ('layout', 'script', 'gfx', 'style', 'net')
    TEST_DIRS_TO_CHECK = ('ref', 'wpt', 'unit',
                          'compiletest/plugin/compile-fail')
    TEST_FILES_TO_CHECK = [
        '{0}/{1}'.format('components/script/dom', test_file)
        for test_file in ['testbinding.rs',
                          'webidls/TestBinding.webidl',
                          'testbindingproxy.rs',
                          'webidls/TestBindingProxy.webidl',
                          'testbindingiterable.rs',
                          'webidls/TestBindingIterable.webidl',
                          'testbindingpairiterable.rs',
                          'webidls/TestBindingPairIterable.webidl']
        ]

    def on_pr_opened(self, api, payload):
        components_changed = set()

        for filepath in api.get_changed_files():
            for component in self.COMPONENT_DIRS_TO_CHECK:
                if 'components/{0}/'.format(component) in filepath:
                    components_changed.add(component)

            for directory in self.TEST_DIRS_TO_CHECK:
                if 'tests/{0}'.format(directory) in filepath:
                    return

            for test_file in self.TEST_FILES_TO_CHECK:
                if test_file in filepath:
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
