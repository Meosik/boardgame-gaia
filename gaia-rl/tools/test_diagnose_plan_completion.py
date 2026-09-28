import unittest

from diagnose_plan_completion import digest, federation_status, inherited_clock


class CompletionDiagnosisTests(unittest.TestCase):
    def test_saved_json_and_live_dataclass_sequences_compare_canonically(self):
        self.assertEqual(digest({'steps': (), 'sources': ('B06',)}),
                         digest({'sources': ['B06'], 'steps': []}))

    def snapshot(self):
        # Structural accounting fixture; legality comes only from native candidates.
        player = dict(faction='Ambas', resources={}, tech_tiles=[6], covered_tech_tiles=[],
                      structures=[dict(hex='0,0', kind='PlanetaryInstitute'),
                                  dict(hex='2,0', kind='ResearchLab'),
                                  dict(hex='3,0', kind='Mine')], federated_hexes=['3,0'])
        return dict(decision_id=1, player=0, state=dict(round=4, players=[player]), candidates=[])

    def test_power_excludes_old_federation_and_includes_active_technology6(self):
        result = federation_status(self.snapshot(), 0, '0,0')
        self.assertEqual(result['total_unfederated_power'], 6)
        self.assertEqual(result['power_deficit'], 1)
        self.assertEqual(result['legal_target_federations'], 0)

    def test_enough_power_is_not_proof_of_a_legal_federation(self):
        snapshot = self.snapshot()
        snapshot['state']['players'][0]['federated_hexes'] = []
        result = federation_status(snapshot, 0, '0,0')
        self.assertEqual(result['power_deficit'], 0)
        self.assertEqual(result['legal_federations'], 0)

    def test_covered_technology_does_not_contribute(self):
        snapshot = self.snapshot()
        snapshot['state']['players'][0]['covered_tech_tiles'] = [6]
        self.assertEqual(federation_status(snapshot, 0, '0,0')['total_unfederated_power'], 5)

    def test_clock_does_not_reset_or_use_future_receipts(self):
        spent = [['3', d] for d in [2, 3, 7, 14, 46, 67]] + [['1', 70]]
        checkpoint = {'memory': {'_clock': {'spent': spent}}}
        self.assertEqual(inherited_clock(checkpoint, 66).remaining(3), 1)
        clock = inherited_clock(checkpoint, 67)
        self.assertEqual(clock.remaining(3), 0)
        self.assertEqual(clock.remaining(1), 6)
        self.assertEqual(checkpoint['memory']['_clock']['spent'], spent)


if __name__ == '__main__':
    unittest.main()
