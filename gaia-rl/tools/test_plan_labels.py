"""plan_labels: label credit and the per-family comparison tally (E74)."""
import unittest

import plan_labels as pl


class PlanLabelTests(unittest.TestCase):
    def test_via_credits_the_plan_behind_every_label_form(self):
        self.assertEqual(pl.via_of('BGG-R1-1RL+2M via BGG-R1-1RL+2M'), 'BGG-R1-1RL+2M')
        self.assertEqual(pl.via_of('value-max Geodens-PI@1,-1-new-type@2,-1'), 'Geodens-PI@1,-1-new-type@2,-1')
        self.assertEqual(pl.via_of('menu-tie federation-2'), 'federation-2')
        self.assertEqual(pl.via_of('current-choice'), 'current-choice')
        self.assertEqual(pl.via_of(None), '')

    def test_family_tally_counts_entries_picks_and_loss_margins(self):
        rows = [
            {'selected': 'current-choice', 'compared': [
                {'goal': 'current-choice', 'value': 265.9, 'complete': True},
                {'goal': 'federation-2', 'value': 230.4, 'complete': True},
                {'goal': 'Geodens-new-type@-3,-1', 'value': 265.9, 'complete': True}]},
            {'selected': 'value-max federation-5', 'compared': [
                {'goal': 'current-choice', 'value': 250.0, 'complete': True},
                {'goal': 'federation-5', 'value': 260.0, 'complete': True},
                {'goal': 'flip-3', 'value': None, 'complete': False}]},
            {'selected': 'local-baseline', 'compared': []},
        ]
        table = pl.family_rows(rows, 'Geodens')
        self.assertEqual((table['federation']['entered'], table['federation']['picked'], table['federation']['lost']),
                         (2, 1, 1))
        self.assertAlmostEqual(table['federation']['margin_sum'], 35.5, places=6)
        self.assertEqual((table['ability']['entered'], table['ability']['picked']), (1, 0))
        self.assertEqual(table['token']['entered'], 0)   # the incomplete flip plan does not count


if __name__ == '__main__':
    unittest.main()
