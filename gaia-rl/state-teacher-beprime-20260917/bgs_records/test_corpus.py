"""Mirror and crawl tests. The transport is faked, so no test reaches the network."""
import json
import tempfile
import unittest
from pathlib import Path

from bgs_records import fixture, source
from bgs_records.corpus import Corpus, CorpusError, sync
from bgs_records.timeline import RecordError


def fake_transport(pages, games, calls=None):
    def transport(url, timeout):
        if calls is not None:
            calls.append(url)
        if '/game/status/ended' in url:
            skip = int(url.split('skip=')[1])
            return json.dumps(pages.get(skip, [])).encode()
        game_id = url.split('/gameplay/')[1].split('/')[0]
        if game_id not in games:
            raise ConnectionError(f'no such game {game_id}')
        return json.dumps(games[game_id]).encode()
    return transport


def fetcher(pages, games, calls=None):
    return source.Fetcher(fake_transport(pages, games, calls), min_interval=0,
                          attempts=1, sleep=lambda _seconds: None)


class MirrorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.corpus = Corpus(Path(self.directory.name), now=lambda: '2026-01-01T00:00:00Z')

    def tearDown(self):
        self.directory.cleanup()

    def test_a_stored_game_reads_back_as_the_same_record(self):
        self.corpus.store('Test-game-0001', fixture.data(), fixture.summary())
        self.assertIn('Test-game-0001', self.corpus)
        record = self.corpus.record('Test-game-0001')
        self.assertEqual(record.seats[0].victory_points, 24)
        self.assertEqual(record.seats[0].ranking, 1)

    def test_the_index_records_provenance_for_every_game(self):
        stored = self.corpus.store('Test-game-0001', fixture.data(), fixture.summary())
        self.assertEqual(stored.fetched_at, '2026-01-01T00:00:00Z')
        self.assertEqual((stored.nb_players, stored.engine_version), (2, '4.8.51'))
        self.assertEqual(len(stored.digest), 64)

    def test_a_game_that_cannot_be_normalised_is_never_stored(self):
        with self.assertRaises(RecordError):
            self.corpus.store('bad', fixture.data(ended=False), None)
        self.assertNotIn('bad', self.corpus)
        self.assertEqual(len(self.corpus), 0)

    def test_a_tampered_mirror_file_is_caught_on_read(self):
        self.corpus.store('Test-game-0001', fixture.data(), fixture.summary())
        path = Path(self.directory.name) / 'games' / 'Test-game-0001.json.gz'
        path.write_bytes(b'\x1f\x8b' + b'0' * 32)
        with self.assertRaises(Exception):
            self.corpus.raw('Test-game-0001')

    def test_a_reopened_corpus_still_knows_what_it_holds(self):
        self.corpus.store('Test-game-0001', fixture.data(), fixture.summary())
        reopened = Corpus(Path(self.directory.name))
        self.assertEqual(reopened.ids(), ('Test-game-0001',))

    def test_an_index_from_another_version_is_refused(self):
        (Path(self.directory.name) / 'index.json').write_text(
            json.dumps({'version': 99, 'games': {}}))
        with self.assertRaises(CorpusError):
            Corpus(Path(self.directory.name))


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.corpus = Corpus(Path(self.directory.name))
        self.summary = fixture.summary()
        other = {'_id': 'powergrid-1', 'status': 'ended', 'cancelled': False,
                 'game': {'name': 'powergrid'}}
        cancelled = {**self.summary, '_id': 'Test-game-0002', 'cancelled': True}
        self.pages = {0: [other, self.summary, cancelled], 50: []}
        self.games = {'Test-game-0001': fixture.data(), 'Test-game-0002': fixture.data()}

    def tearDown(self):
        self.directory.cleanup()

    def test_only_finished_uncancelled_gaia_games_are_mirrored(self):
        report = sync(self.corpus, fetcher(self.pages, self.games), wanted=10)
        self.assertEqual(self.corpus.ids(), ('Test-game-0001',))
        self.assertEqual((report.added, report.scanned), (1, 1))
        self.assertTrue(report.exhausted)

    def test_a_second_crawl_re_downloads_nothing(self):
        calls = []
        sync(self.corpus, fetcher(self.pages, self.games), wanted=10)
        sync(self.corpus, fetcher(self.pages, self.games, calls), wanted=10)
        self.assertEqual(len(self.corpus), 1)
        self.assertFalse([url for url in calls if '/gameplay/' in url])

    def test_a_setup_filter_skips_the_download_entirely(self):
        # The listing states the player count, so a two-player game costs one row.
        two_player = {**self.summary, 'players': [{'name': 'a'}, {'name': 'b'}]}
        four_player = {**self.summary, '_id': 'Test-game-0004',
                       'players': [{'name': c} for c in 'abcd']}
        pages = {0: [two_player, four_player], 50: []}
        games = {'Test-game-0004': fixture.data()}   # the 2p game is never fetched
        calls = []
        report = sync(self.corpus, fetcher(pages, games, calls), wanted=10, players=4)
        self.assertEqual(report.scanned, 1)
        self.assertFalse([url for url in calls if 'Test-game-0001' in url])

    def test_an_expansion_filter_also_works_off_the_listing(self):
        base = self.summary
        expansion = {**self.summary, '_id': 'Test-game-0005',
                     'game': {'name': 'gaia-project', 'expansions': ['lost-fleet']}}
        pages = {0: [base, expansion], 50: []}
        calls = []
        sync(self.corpus, fetcher(pages, {'Test-game-0005': fixture.data()}, calls),
             wanted=10, lost_fleet=True)
        self.assertFalse([url for url in calls if 'Test-game-0001' in url])

    def test_the_crawl_stops_once_it_has_what_was_asked_for(self):
        report = sync(self.corpus, fetcher(self.pages, self.games), wanted=0)
        self.assertEqual((report.added, len(self.corpus)), (0, 0))

    def test_an_unusable_game_is_reported_and_the_crawl_continues(self):
        broken = {**fixture.data(), 'ended': False}
        report = sync(self.corpus, fetcher(self.pages, {'Test-game-0001': broken}), wanted=5)
        self.assertEqual(report.added, 0)
        self.assertEqual([game_id for game_id, _reason in report.rejected], ['Test-game-0001'])


class FetcherTests(unittest.TestCase):
    def test_a_failing_request_is_retried_then_surfaced(self):
        attempts = []

        def transport(url, timeout):
            attempts.append(url)
            raise ConnectionError('down')

        client = source.Fetcher(transport, min_interval=0, attempts=3,
                                sleep=lambda _seconds: None)
        with self.assertRaises(source.SourceError):
            client.json('/game/status/ended?count=1&skip=0')
        self.assertEqual(len(attempts), 3)

    def test_a_non_json_answer_is_refused(self):
        client = source.Fetcher(lambda url, timeout: b'<html>nope</html>', min_interval=0,
                                sleep=lambda _seconds: None)
        with self.assertRaises(source.SourceError):
            client.json('/game/status/ended?count=1&skip=0')

    def test_requests_are_paced_apart(self):
        naps = []
        client = source.Fetcher(lambda url, timeout: b'[]', min_interval=0.25,
                                sleep=naps.append, clock=lambda: 0.0)
        client.json('/game/status/ended?count=1&skip=0')
        client.json('/game/status/ended?count=1&skip=50')
        self.assertEqual(naps, [0.25])


if __name__ == '__main__':
    unittest.main()
