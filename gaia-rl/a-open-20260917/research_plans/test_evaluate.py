import unittest

from current_actions.teacher import CurrentActionTeacher
from research_plans.evaluate import teacher_for_variant
from research_plans.teacher import ResearchPlanTeacher


class ComparisonTests(unittest.TestCase):
    def test_control_and_candidate_keep_identical_purpose_stage(self):
        control, candidate = teacher_for_variant(0), teacher_for_variant(1)
        self.assertIs(type(control), CurrentActionTeacher)
        self.assertIs(type(candidate), ResearchPlanTeacher)
        self.assertEqual(control.stage, candidate.stage)
        self.assertEqual(control.stage, 1)
        with self.assertRaises(ValueError):
            teacher_for_variant(2)


if __name__ == '__main__':
    unittest.main()
