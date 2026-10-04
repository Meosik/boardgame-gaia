"""explain_decision rebuilds a recorded decision and shows the teacher's ranking and plans."""
from pathlib import Path
import tempfile
import unittest

import explain_decision
from test_ab_replays import fake_game


class ExplainDecisionTests(unittest.TestCase):
    def test_a_recorded_decision_is_rebuilt_and_explained(self):
        game = fake_game(Path(tempfile.mkdtemp()))
        text = explain_decision.explain(game, 60, 3, 'tools/teacher-a-search2-h1-geodens.json', 0)
        self.assertIn('결정 60', text)
        self.assertIn('실제로 둔 수: [28]', text)
        self.assertIn('기본 순위', text)
        self.assertIn('★ [28]', text)


if __name__ == '__main__':
    unittest.main()
