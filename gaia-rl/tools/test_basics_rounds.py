import math
import unittest

import basics_rounds as br


def seat(stock, income, passes):
    full = lambda v: dict(zip(br.KEYS, v))
    return {'stock4': full(stock), 'income': full(income),
            'passes': [{'round': r, 'builds': b, 'resources': full(res)} for r, b, res in passes]}


class SummarizeTests(unittest.TestCase):
    def test_means_per_arm_over_pairs_with_both_arms(self):
        records = {
            ('pair-000', 'Xenos'): {'A': seat((4, 10, 2, 1), (20, 30, 6, 2), [(1, 2, (0, 4, 0, 0)), (2, 4, (2, 4, 0, 2))]),
                                    'B': seat((2, 20, 4, 3), (10, 20, 8, 0), [(1, 0, (4, 0, 0, 0))])},
            ('pair-001', 'Xenos'): {'A': seat((6, 14, 4, 1), (22, 34, 8, 2), [])},   # one arm missing: left out
            ('pair-002', 'Taklons'): {'A': seat((1, 1, 1, 1), (0, 0, 0, 0), [])},
        }
        table = br.summarize(records)
        x = table['Xenos']
        self.assertEqual(x['pairs'], 1)
        self.assertEqual(x['A']['stock4'], {'ore': 4, 'credits': 10, 'knowledge': 2, 'qic': 1})
        self.assertEqual(x['B']['income']['credits'], 20)
        self.assertEqual(x['A']['pass_builds'], 3)
        self.assertEqual(x['A']['pass_stock'], (4 + 8) / 2)
        self.assertEqual(x['A']['pass_parts']['ore'], 1)
        self.assertEqual(x['B']['pass_builds'], 0)
        self.assertEqual(table['Taklons']['pairs'], 0)
        self.assertIsNone(table['Taklons']['A'])

    def test_arm_without_passes_gives_nan_and_text_table_prints(self):
        records = {('pair-000', 'Xenos'): {'A': seat((1, 2, 3, 4), (1, 1, 1, 1), []),
                                           'B': seat((2, 2, 2, 2), (1, 1, 1, 1), [(3, 5, (1, 1, 1, 1))])}}
        table = br.summarize(records)
        self.assertTrue(math.isnan(table['Xenos']['A']['pass_builds']))
        text = br.text_table(table)
        self.assertIn('Xenos', text)
        self.assertIn('1.0/2.0/3.0/4.0 | 2.0/2.0/2.0/2.0', text)
        self.assertIn('5.0', text)


if __name__ == '__main__':
    unittest.main()
