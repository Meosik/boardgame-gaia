"""publish_faction_replays.py: the median-charge seat pick."""
import unittest

from publish_faction_replays import group_by_game, pick_median_seats


class PickTests(unittest.TestCase):
    def test_picks_the_seat_closest_to_each_factions_median(self):
        seats = {
            'pair-001/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 2}, {'faction': 'Y', 'arm': 'A', 'charges': 10}],
            'pair-002/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 6}, {'faction': 'Y', 'arm': 'B', 'charges': 4}],
            'pair-003/game-0-A00': [{'faction': 'Y', 'arm': 'A', 'charges': 7}, {'faction': 'X', 'arm': 'B', 'charges': 9}],
        }
        picks = pick_median_seats(seats)
        self.assertEqual(picks['X'], ('pair-002/game-0-A00', 0, 6, 6))
        self.assertEqual(picks['Y'], ('pair-003/game-0-A00', 0, 7, 7))

    def test_group_by_game(self):
        seats = {
            'pair-001/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 2}, {'faction': 'Y', 'arm': 'A', 'charges': 10}],
            'pair-002/game-0-A00': [{'faction': 'X', 'arm': 'A', 'charges': 6}, {'faction': 'Y', 'arm': 'B', 'charges': 4}],
            'pair-003/game-0-A00': [{'faction': 'Y', 'arm': 'A', 'charges': 7}, {'faction': 'X', 'arm': 'B', 'charges': 9}],
        }
        groups = group_by_game(pick_median_seats(seats))
        self.assertEqual(groups, {'pair-002/game-0-A00': [('X', 0, 6, 6)],
                                  'pair-003/game-0-A00': [('Y', 0, 7, 7)]})
        shared = {'pair-004/game-0-A01': [{'faction': 'Z', 'arm': 'A', 'charges': 5}, {'faction': 'W', 'arm': 'B', 'charges': 3}]}
        self.assertEqual(group_by_game(pick_median_seats(shared)),
                         {'pair-004/game-0-A01': [('W', 1, 3, 3), ('Z', 0, 5, 5)]})


class AllGamesTests(unittest.TestCase):
    def test_all_games_exports_every_game_at_focus_zero_without_charges_json(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        import publish_faction_replays as module
        import publish_replays
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)/'run'
            games = ['pair-000/game-0-A02', 'pair-000/game-1-A03', 'pair-001/game-0-A04']
            for game in games:
                (run_dir/game).mkdir(parents=True)
            commands = []
            def fake_run(command, env):
                commands.append(command)
                return 0
            argv = ['publish_faction_replays.py', str(run_dir), '--destination', str(Path(tmp)/'dest'),
                    '--output', str(Path(tmp)/'out'), '--all-games', '--also', 'pair-009/game-0-A99']
            with mock.patch.object(module, 'run', fake_run), \
                 mock.patch.object(publish_replays, 'read_catalog', lambda path: []), \
                 mock.patch.object(publish_replays, 'write_catalog', lambda path, catalog: None), \
                 mock.patch('sys.argv', argv):
                self.assertEqual(module.main(), 0)
        exports = [c for c in commands if 'export' in c]
        self.assertEqual([c[c.index('export') + 1] for c in exports], [str(run_dir/game) for game in games])
        self.assertTrue(all(c[c.index('--focus') + 1] == '0' for c in exports))
        self.assertEqual(len(commands), len(games) + 1)


if __name__ == '__main__':
    unittest.main()
