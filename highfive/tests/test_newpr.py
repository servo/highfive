from highfive import newpr
from highfive.tests import base

class TestNewPR(base.BaseTest):

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
