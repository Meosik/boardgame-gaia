"""Observation tests. The catalog must count, keep its sample size, and claim nothing more."""
import unittest

from bgs_records import fixture
from bgs_records.catalog import THIN_SAMPLE, Observation, Tally, build as build_catalog
from bgs_records.catalog import summarise
from bgs_records.timeline import build


def record():
    return build('Test-game-0001', fixture.data(), fixture.summary())


class TallyTests(unittest.TestCase):
    def test_a_figure_always_carries_the_sample_it_came_from(self):
        tally = Tally()
        tally.add('2M+1TS', 150, True)
        tally.add('2M+1TS', 130, False)
        observation, = tally.observations()
        self.assertEqual((observation.games, observation.wins), (2, 1))
        self.assertEqual(observation.average_score, 140)
        self.assertEqual(observation.win_rate, 0.5)

    def test_a_thin_sample_is_reported_and_flagged_rather_than_smoothed(self):
        thin = Observation('rare', THIN_SAMPLE - 1, 100.0, 0)
        wide = Observation('common', THIN_SAMPLE, 100.0, 0)
        self.assertTrue(thin.is_thin)
        self.assertFalse(wide.is_thin)
        self.assertTrue(thin.as_dict()['thin_sample'])

    def test_observations_come_back_widest_sample_first(self):
        tally = Tally()
        for _ in range(3):
            tally.add('often', 100, False)
        tally.add('rarely', 100, False)
        self.assertEqual([o.label for o in tally.observations()], ['often', 'rarely'])


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = build_catalog([record()])

    def test_each_seat_is_counted_once(self):
        self.assertEqual((self.catalog.games, self.catalog.seats), (1, 2))

    def test_setups_are_kept_apart_so_they_are_never_pooled_by_accident(self):
        self.assertEqual([row['label'] for row in self.catalog.setups], ['2p/standard'])

    def test_faction_rows_carry_scores_and_wins(self):
        terrans = next(r for r in self.catalog.factions if r['label'] == 'terrans')
        self.assertEqual((terrans['games'], terrans['wins']), (1, 1))
        self.assertEqual(terrans['average_score'], 24)
        self.assertTrue(terrans['thin_sample'])

    def test_an_opening_is_what_stood_when_round_one_ended(self):
        openings = self.catalog.openings['terrans']
        self.assertEqual([row['label'] for row in openings], ['1RL+1M'])

    def test_opening_labels_use_the_bgg_table_ordering(self):
        # Biggest building first, so a label is the same string `bgg_openings` uses and
        # the two sources compare without translation.
        from bgg_openings.catalog import parse_buildings
        label = self.catalog.openings['terrans'][0]['label']
        self.assertEqual(label.split('+')[0][-2:], 'RL')
        self.assertEqual(parse_buildings(label).research_lab, 1)
        self.assertEqual(parse_buildings(label).mine, 1)

    def test_boosters_are_counted_in_the_round_they_were_taken(self):
        self.assertIn('setup', self.catalog.boosters_by_round)
        self.assertEqual([row['label'] for row in self.catalog.boosters_by_round['round1']],
                         ['booster5'])

    def test_first_federation_round_is_recorded_per_seat(self):
        labels = {row['label']: row['games'] for row in self.catalog.federation_round}
        self.assertEqual(labels, {'round1': 1, 'none': 1})

    def test_vp_sources_total_across_the_corpus(self):
        sources = {row['source']: row['total_vp'] for row in self.catalog.vp_sources}
        self.assertEqual(sources['federation'], 7)
        self.assertEqual(sources['charge'], -1)

    def test_an_empty_corpus_supports_no_observations(self):
        with self.assertRaises(ValueError):
            build_catalog([])

    def test_the_summary_reads_as_text_without_inventing_figures(self):
        text = summarise(self.catalog)
        self.assertIn('1 games, 2 seats', text)
        self.assertIn('terrans', text)


if __name__ == '__main__':
    unittest.main()
