"""Check diagnostic fixture legality and native effects without tuning signs."""
import unittest

from diagnose_research_bc import access_rows, delta, research_rows, tech_rows, token_rows


class ResearchDiagnosticTests(unittest.TestCase):
    def test_paid_research_spends_four_knowledge_and_advances_once(self):
        rows = research_rows()
        self.assertEqual(len(rows), 12)
        for row in rows:
            key = row['track']
            self.assertEqual(row['tracks_after'][key]-row['tracks_before'][key], 1)
            self.assertEqual(sum(row['tracks_after'].values())-sum(row['tracks_before'].values()), 1)
            self.assertEqual(row['resources_before']['knowledge']-row['resources_after']['knowledge'], 4)
            self.assertEqual(row['after_breakdown']['research_progress'], 0)
            self.assertAlmostEqual(row['delta'], sum(v['delta'] for v in row['changed_breakdown'].values()))

    def test_reach_and_terraform_costs_come_from_native_rules(self):
        for row in access_rows():
            if row['track'] == 'navigation':
                self.assertEqual((len(row['options_before']), len(row['options_after'])), (0, 1))
                self.assertEqual(row['options_after'][0]['qic'], 0)
                self.assertGreater(delta(row, 'expansion_opportunity'), 0)
            else:
                before, after = row['options_before'][0], row['options_after'][0]
                self.assertEqual(before['ore']-after['ore'],
                    before['terraform_steps']*(row['rule_effect_before']-row['rule_effect_after']))
                self.assertGreaterEqual(delta(row, 'expansion_opportunity'), 0)
                if row['rule_effect_before'] == row['rule_effect_after']:
                    self.assertAlmostEqual(delta(row, 'expansion_opportunity'), 0)

    def test_tech_always_includes_free_research_with_all_lower_row_choices(self):
        rows = tech_rows()
        self.assertEqual(len(rows), 16)
        for row in rows:
            self.assertEqual(row['advance'][2]-row['advance'][1], 1)
            self.assertEqual(row['resources_after']['knowledge'], row['resources_before']['knowledge'])
            if row['tile'] == 4:
                self.assertEqual(row['advance'][0], 'navigation')
                self.assertEqual(row['resources_after']['qic']-row['resources_before']['qic'], 1)
            elif row['tile'] == 10:
                self.assertEqual(row['advance'][0], 'science')
                # Tile10's charge action is not counted as income.
                self.assertEqual(row['income_before']['power_charge'], row['income_after']['power_charge'])

    def test_ore_to_token_gains_no_future_income_with_or_without_shortage(self):
        for row in token_rows():
            for name, value in row['values'].items():
                expected = -.54 if row['active_tokens'] == 3 and '+b' in name else -2.67
                self.assertAlmostEqual(value['delta'], expected)
                self.assertEqual(delta(value, 'future_income'), 0)
                self.assertTrue(value['passed'])


if __name__ == '__main__':
    unittest.main()
