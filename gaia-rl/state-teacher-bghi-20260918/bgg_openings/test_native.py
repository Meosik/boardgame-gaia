"""Real rules/transition smoke tests, not teacher-opening quality demonstrations."""
import json
from pathlib import Path
import unittest

from gaia_rl import Environment
from gaia_rl.versions import require_current_sources
from bgg_openings.catalog import BASE_FACTIONS, load_catalog
from bgg_openings.inventory import building_counts, matches, round_one_result


class NativeInventoryTests(unittest.TestCase):
    def test_real_round_one_boundaries_cover_all_source_factions(self):
        require_current_sources(Path(__file__).resolve().parents[3])
        seen = set()
        catalog = load_catalog()
        for number in range(30):
            env = Environment(f'bgg-inventory-boundary-{number}', 2000)
            before = json.loads(env.snapshot_json())
            for _ in range(100):
                # End R1 quickly to test its boundary; not a human or teacher policy.
                index = next((i for i, c in enumerate(before['candidates'])
                              if c['action']['type'] == 'Pass'), 0)
                env.step(before['decision_id'], index)
                after = json.loads(env.snapshot_json())
                if before['state']['round'] == 1 and after['state']['round'] == 2:
                    for player in before['state']['players']:
                        count = building_counts(player)
                        self.assertEqual(count.academy, 0)
                        result = round_one_result(before, after, player['player_id'])
                        self.assertEqual(result, tuple(o for o in catalog.get(player['faction'], ())
                                                       if matches(player, o)))
                        seen.add(player['faction'])
                    break
                before = after
            else:
                self.fail('No native R1->R2 boundary within the bounded smoke run')
            if BASE_FACTIONS <= seen:
                break
        self.assertTrue(BASE_FACTIONS <= seen, BASE_FACTIONS - seen)


if __name__ == '__main__':
    unittest.main()
