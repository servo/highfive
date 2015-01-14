import os

import testtools

from highfive import newpr


class BaseTest(testtools.TestCase):

    def _load_fake(self, fake):
        fakes_dir = os.path.join(os.path.dirname(__file__), 'fakes')

        with open(os.path.join(fakes_dir, fake)) as fake:
            return fake.read()


class TestNewPR(BaseTest):

    def test_submodule(self):
        submodule_diff = self._load_fake('submodule.diff')
        self.assertTrue(newpr.modifies_submodule(submodule_diff))

        normal_diff = self._load_fake('normal.diff')
        self.assertFalse(newpr.modifies_submodule(normal_diff))


    def test_choose_reviewer(self):
        normal_diff = self._load_fake('normal.diff')
        reviewer = newpr.choose_reviewer('rust',
                                         'rust-lang',
                                         normal_diff,
                                         'nikomatsakis')
        self.assertNotEqual('nikomatsakis', reviewer)
