from pathlib import Path
import unittest
from unittest.mock import patch

from current_actions.teacher import CurrentActionTeacher
from research_plans.evaluate import sources_for_comparison, teacher_for_variant
from resource_plans.evaluate import main
from resource_plans.teacher import ResourcePlanTeacher


class ResourceEvaluationTests(unittest.TestCase):
    def test_explicit_candidate_preserves_the_current_stage_one_control(self):
        self.assertIs(type(teacher_for_variant(0, ResourcePlanTeacher)), CurrentActionTeacher)
        candidate = teacher_for_variant(1, ResourcePlanTeacher)
        self.assertIs(type(candidate), ResourcePlanTeacher)
        self.assertEqual(candidate.stage, 1)

    def test_runner_and_fixture_are_scoped_to_xenos(self):
        with patch('resource_plans.evaluate.compare') as compare:
            main()
        kwargs = compare.call_args.kwargs
        self.assertEqual(kwargs['faction'], 'Xenos')
        self.assertIs(kwargs['candidate_factory'], ResourcePlanTeacher)
        sources = sources_for_comparison(kwargs['fixture_dirs'])
        self.assertIn('gaia-rl/experiments/resource_plans/fixtures/xenos75.json', sources)
        self.assertIn('gaia-rl/experiments/resource_plans/teacher.py', sources)


if __name__ == '__main__':
    unittest.main()
