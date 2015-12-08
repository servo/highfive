from eventhandler import EventHandler

reftest_required_msg = 'These commits modify layout code, but no reftests are modified. Please consider adding a reftest!'
unittest_required_msg = 'These commits are likely to require unit tests, but no unit tests are modified. Please consider adding a unit test!'


class MissingTestHandler(EventHandler):
    def on_pr_opened(self, api, payload):
        diff = api.get_diff()
        layout_changed = False
        unittestable_code_changed = False
        layout_tests_present = False
        unittests_present = False

        for line in diff.split('\n'):
            if self.layout_tests_present(line):
                layout_tests_present = True
            if self.unittests_present(line):
                unittests_present = True
            if unittests_present and layout_tests_present:
                return

            if self.layout_changed(line):
                layout_changed = True
            if self.unittestable_code_changed(line):
                unittestable_code_changed = True

        if layout_changed and not layout_tests_present:
            self.warn(reftest_required_msg)
        if unittestable_code_changed and not unittests_present:
            self.warn(unittest_required_msg)

    def unittests_present(self, line):
        return (
            line.startswith('diff --git') and
            line.find('tests/unit') > -1)

    def unittestable_code_changed(self, line):
        return (
            line.startswith('diff --git') and
            (line.find('components/script/') > -1 or
                line.find('components/gfx/') > -1 or
                line.find('components/style/') > -1 or
                line.find('components/net/') > -1))

    def layout_tests_present(self, line):
        return (
            line.startswith('diff --git') and
            (line.find('tests/ref') > -1
                or line.find('tests/wpt') > -1))

    def layout_changed(self, line):
        return (
            line.startswith('diff --git') and
            line.find('components/layout/') > -1)

handler_interface = MissingTestHandler
