import unittest

from faction_teachers.diagnostics import summarize_candidate_limits


class CandidateLimitTests(unittest.TestCase):
    def test_missing_historical_diagnostics_are_unknown_not_zero(self):
        rows = [{'audit': {}}, {'audit': {'candidate_generation': None}},
                {'audit': {'candidate_generation': {
                    'federation_limit_hits': 0, 'federation_limit_reasons': []}}},
                {'audit': {'candidate_generation': {
                    'federation_limit_hits': 1, 'federation_limit_reasons': ['search work']},
                    'plans': [{'candidate_generation': {'federation_limit_hits': 99}}]}}]
        result = summarize_candidate_limits(rows)
        self.assertEqual(result['audited_decisions'], 2)
        self.assertEqual(result['unknown_decisions'], 2)
        self.assertEqual(result['federation_limit_hits'], 1)
        self.assertEqual(result['federation_limit_reasons'], {'search work': 1})

    def test_invalid_counts_cannot_be_published_as_success(self):
        for count, labels in ((True, ['search work']), (-1, []), (1, []), (0, [3])):
            with self.subTest(count=count), self.assertRaises(ValueError):
                summarize_candidate_limits([{'audit': {'candidate_generation': {
                    'federation_limit_hits': count, 'federation_limit_reasons': labels}}}])


if __name__ == '__main__':
    unittest.main()
