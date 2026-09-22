"""Runs against the real mirror when one exists: the guard against upstream drift.

The site keeps releasing its engine, and a new notation would otherwise show up as
quietly missing training rows. These tests do nothing when no mirror has been fetched,
so a fresh checkout still passes; `python -m bgs_records fetch` turns them on.

A mirror grows to thousands of games and rebuilding all of them costs minutes, which is
enough to stop anyone running the suite. These check an evenly strided sample spanning
the whole mirror — drift shows up in any slice of it — and `BGS_MIRROR_FULL=1` sweeps
everything for a release check.
"""
import os
import unittest
from pathlib import Path

from bgs_records.corpus import Corpus
from bgs_records.dataset import REQUIRED_FIELDS, rows
from bgs_records.state import verify
from bgs_records.timeline import LAST_ROUND, STARTING_VP

MIRROR = Path(__file__).resolve().parents[2] / 'research/bgs-records'
SAMPLE = 150
#: A few records genuinely will not reconstruct — a research level the log never explains,
#: say — and the pipeline's answer is to drop those games. So the check is that the share
#: stays tiny, not that it is zero: a notation change would push it far past this, while a
#: one-off oddity should not fail the suite for something the design already handles.
MAX_UNVERIFIED = 0.01


def mirror() -> Corpus | None:
    if not (MIRROR / 'index.json').exists():
        return None
    corpus = Corpus(MIRROR)
    return corpus if len(corpus) else None


def sampled(corpus: Corpus) -> tuple[str, ...]:
    """An evenly strided slice of the mirror, or all of it under BGS_MIRROR_FULL."""
    ids = corpus.ids()
    if os.environ.get('BGS_MIRROR_FULL') or len(ids) <= SAMPLE:
        return ids
    stride = len(ids) / SAMPLE
    return tuple(ids[int(i * stride)] for i in range(SAMPLE))


@unittest.skipIf(mirror() is None, f'no mirror at {MIRROR}; run `python -m bgs_records fetch`')
class MirrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = mirror()
        cls.ids = sampled(cls.corpus)
        cls.records = [cls.corpus.record(game_id) for game_id in cls.ids]

    def test_every_sampled_game_still_parses(self):
        self.assertEqual(self.corpus.rejected(self.ids), ())

    def test_every_game_runs_the_full_six_rounds(self):
        for record in self.records:
            with self.subTest(game=record.game_id):
                self.assertEqual(max(t.round for t in record.turns), LAST_ROUND)

    def test_logged_victory_points_reconstruct_every_recorded_score(self):
        for record in self.records:
            totals = dict.fromkeys((s.seat for s in record.seats), STARTING_VP)
            for effect in record.effects:
                if effect.resource == 'vp':
                    totals[effect.seat] += effect.delta
            with self.subTest(game=record.game_id):
                self.assertEqual(totals, {s.seat: s.victory_points for s in record.seats})

    def test_nearly_every_rebuild_verifies_against_its_recorded_final_board(self):
        unverified = [record.game_id for record in self.records
                      if not set(REQUIRED_FIELDS) <= set(
                          verify(record, self.corpus.raw(record.game_id)['data']))]
        share = len(unverified) / len(self.records)
        self.assertLessEqual(
            share, MAX_UNVERIFIED,
            f'{len(unverified)} of {len(self.records)} games did not verify '
            f'({share:.1%}): {unverified[:5]}')

    def test_every_verified_game_yields_decisions(self):
        # A game that verifies must produce rows; one that does not is meant to produce
        # none, and `dataset.rows` returning nothing for it is the intended behaviour.
        for record in self.records:
            final_board = self.corpus.raw(record.game_id)['data']
            if not set(REQUIRED_FIELDS) <= set(verify(record, final_board)):
                continue
            with self.subTest(game=record.game_id):
                self.assertTrue(any(True for _ in rows(record, final_board)))


if __name__ == '__main__':
    unittest.main()
