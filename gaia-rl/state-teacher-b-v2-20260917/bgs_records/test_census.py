"""Census tests. The listing is faked, so no test reaches the network."""
import json
import unittest

from bgs_records import census, source


def listing(entries, total):
    def transport(url, timeout):
        if url.endswith('/count'):
            return json.dumps(total).encode()
        skip = int(url.split('skip=')[1].split('&')[0])
        count = int(url.split('count=')[1].split('&')[0])
        return json.dumps(entries[skip:skip + count]).encode()
    return source.Fetcher(transport, min_interval=0, sleep=lambda _s: None)


def entry(game_id, players=4, expansions=(), name='gaia-project'):
    return {'_id': game_id, 'status': 'ended', 'cancelled': False,
            'game': {'name': name, 'expansions': list(expansions)},
            'players': [{'name': f'p{i}'} for i in range(players)]}


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.entries = (
            [entry(f'four{i}') for i in range(6)]
            + [entry(f'two{i}', players=2) for i in range(3)]
            + [entry('lf4', expansions=('lost-fleet',))]
            + [entry('lf2', players=2, expansions=('lost-fleet',))]
            + [entry('other', name='powergrid')]
            + [{**entry('dropped'), 'cancelled': True}])

    def test_it_counts_setups_without_downloading_any_game(self):
        counted = census.take(listing(self.entries, len(self.entries)))
        self.assertEqual(counted.scanned, len(self.entries))
        self.assertEqual(counted.gaia, 11)   # powergrid and the cancelled game excluded
        self.assertEqual(counted.setups[(4, ())], 6)
        self.assertEqual(counted.setups[(2, ())], 3)

    def test_it_answers_the_question_the_target_setup_depends_on(self):
        counted = census.take(listing(self.entries, len(self.entries)))
        self.assertEqual(counted.count(players=4), 7)
        self.assertEqual(counted.count(expansion='lost-fleet'), 2)
        self.assertEqual(counted.setups[(4, ('lost-fleet',))], 1)

    def test_expansion_games_are_listed_by_id_because_they_are_too_rare_to_find(self):
        counted = census.take(listing(self.entries, len(self.entries)))
        self.assertEqual({g[0] for g in counted.expansion_games}, {'lf4', 'lf2'})

    def test_a_limit_reads_only_that_much_of_the_listing(self):
        counted = census.take(listing(self.entries, len(self.entries)), limit=4)
        self.assertEqual(counted.scanned, 4)
        self.assertEqual(counted.listed, len(self.entries))

    def test_a_start_offset_skips_the_newest_games(self):
        counted = census.take(listing(self.entries, len(self.entries)), start=9, limit=2)
        self.assertEqual({g[0] for g in counted.expansion_games}, {'lf4', 'lf2'})

    def test_the_description_names_every_setup_it_found(self):
        text = census.take(listing(self.entries, len(self.entries))).describe()
        self.assertIn('4p + lost-fleet', text)
        self.assertIn('2p', text)

    def test_an_impossible_window_is_refused(self):
        with self.assertRaises(ValueError):
            census.take(listing([], 0), start=-1)


if __name__ == '__main__':
    unittest.main()
