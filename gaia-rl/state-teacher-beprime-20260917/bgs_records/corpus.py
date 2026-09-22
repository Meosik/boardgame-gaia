"""A resumable on-disk mirror of downloaded games, with provenance for every record.

One directory holds `index.json` and `games/<id>.json.gz`. Each stored game keeps both
halves the site serves: the listing `summary` (final placements and rating changes) and
the `data` engine state (`moveHistory`, `advancedLog`, final board). Re-running `sync`
downloads only what is missing, so a crawl can stop and resume without re-requesting.

The mirror stores what was served, unmodified. Normalising and validating is
`timeline.build`'s job, and happens on read, so a fix there never needs a re-crawl.
"""
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import time

from . import source
from .timeline import GameRecord, RecordError, build

INDEX_VERSION = 1


class CorpusError(RuntimeError):
    """The mirror on disk is not the shape this package wrote."""


@dataclass(frozen=True)
class Stored:
    """What the index knows about a game without opening it.

    Choosing which games to learn from has to be answerable from here: rebuilding the
    whole mirror to decide costs gigabytes of memory and minutes of CPU, and the answer
    only ever depends on the setup and the table's ratings.
    """
    game_id: str
    fetched_at: str
    digest: str
    nb_players: int
    expansions: tuple[str, ...]
    faction_variant: str | None
    engine_version: str | None
    #: Each seat's rating going into the game, in seat order; None where unrated.
    elo: tuple[int | None, ...] = ()

    @property
    def is_lost_fleet(self) -> bool:
        return 'lost-fleet' in self.expansions


def _stored(game_id: str, entry: dict) -> Stored:
    return Stored(game_id, entry.get('fetched_at', ''), entry.get('digest', ''),
                  entry.get('nb_players', 0), tuple(entry.get('expansions') or ()),
                  entry.get('faction_variant'), entry.get('engine_version'),
                  tuple(entry.get('elo') or ()))


def _utc_now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


class Corpus:
    def __init__(self, root: Path, *, now=_utc_now):
        self.root = Path(root)
        self.games = self.root / 'games'
        self._index_path = self.root / 'index.json'
        self._now = now
        self._index = self._read_index()

    def _read_index(self) -> dict:
        if not self._index_path.exists():
            return {'version': INDEX_VERSION, 'games': {}}
        index = json.loads(self._index_path.read_text())
        if index.get('version') != INDEX_VERSION:
            raise CorpusError(f'{self._index_path} has version {index.get("version")!r}')
        if not isinstance(index.get('games'), dict):
            raise CorpusError(f'{self._index_path} has no game table')
        return index

    def _write_index(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        # Written via a temporary file so an interrupted crawl cannot truncate the index.
        temporary = self._index_path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(self._index, indent=1, sort_keys=True))
        temporary.replace(self._index_path)

    def __contains__(self, game_id: str) -> bool:
        return game_id in self._index['games'] and self._path(game_id).exists()

    def __len__(self) -> int:
        return len(self._index['games'])

    def ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._index['games']))

    def _path(self, game_id: str) -> Path:
        if '/' in game_id or game_id in ('.', '..'):
            raise CorpusError(f'Unusable game id: {game_id!r}')
        return self.games / f'{game_id}.json.gz'

    def store(self, game_id: str, data: dict, summary: dict | None) -> Stored:
        """Validate a downloaded game, then mirror it. An unusable record is not stored."""
        record = build(game_id, data, summary)
        payload = json.dumps({'game_id': game_id, 'summary': summary, 'data': data},
                             sort_keys=True).encode()
        self.games.mkdir(parents=True, exist_ok=True)
        with gzip.open(self._path(game_id), 'wb') as stream:
            stream.write(payload)
        entry = self._entry(record, self._now(), hashlib.sha256(payload).hexdigest())
        self._index['games'][game_id] = entry
        self._write_index()
        return _stored(game_id, entry)

    @staticmethod
    def _entry(record: GameRecord, fetched_at: str, digest: str) -> dict:
        return {
            'fetched_at': fetched_at,
            'digest': digest,
            'nb_players': record.options.nb_players,
            'expansions': list(record.options.expansions),
            'faction_variant': record.options.faction_variant,
            'engine_version': record.options.engine_version,
            'elo': [seat.elo_initial for seat in record.seats],
        }

    def entries(self) -> tuple[Stored, ...]:
        """Every mirrored game's index entry. Opens no game files."""
        return tuple(_stored(game_id, self._index['games'][game_id])
                     for game_id in self.ids())

    def reindex(self) -> int:
        """Rewrite index entries from the mirrored files, for fields added since.

        Reads the mirror, never the network. An entry that cannot be rebuilt is left as
        it was rather than dropped — the game file is still there to be read directly.
        """
        rebuilt = 0
        for game_id in self.ids():
            entry = self._index['games'][game_id]
            try:
                record = self.record(game_id)
            except (RecordError, CorpusError):
                continue
            self._index['games'][game_id] = self._entry(
                record, entry.get('fetched_at', ''), entry.get('digest', ''))
            rebuilt += 1
        self._write_index()
        return rebuilt

    def raw(self, game_id: str) -> dict:
        path = self._path(game_id)
        if not path.exists():
            raise CorpusError(f'{game_id} is not mirrored at {path}')
        with gzip.open(path, 'rb') as stream:
            payload = stream.read()
        expected = self._index['games'].get(game_id, {}).get('digest')
        if expected and hashlib.sha256(payload).hexdigest() != expected:
            raise CorpusError(f'{game_id} on disk does not match its indexed digest')
        return json.loads(payload)

    def record(self, game_id: str) -> GameRecord:
        stored = self.raw(game_id)
        return build(game_id, stored['data'], stored.get('summary'))

    def records(self):
        """Yield every mirrored game, newest-stored last. Unusable records are skipped."""
        for game_id in self.ids():
            try:
                yield self.record(game_id)
            except RecordError:
                continue

    def rejected(self, game_ids=None) -> tuple[tuple[str, str], ...]:
        """Mirrored games `timeline.build` refuses, with the reason. Never silently dropped.

        Rebuilds one game at a time and keeps none: the whole mirror rebuilt at once is
        gigabytes, and all this needs is the failures.
        """
        failures = []
        for game_id in (self.ids() if game_ids is None else game_ids):
            try:
                self.record(game_id)
            except RecordError as error:
                failures.append((game_id, str(error)))
        return tuple(failures)


def backfill_summaries(corpus: 'Corpus', fetcher: source.Fetcher,
                       log=lambda message: None) -> tuple[int, int]:
    """Fetch the listing half for mirrored games stored without it.

    Ratings live only in the listing record, so a game mirrored without one cannot be
    filtered by strength. Returns (completed, still missing).
    """
    completed = missing = 0
    for game_id in corpus.ids():
        stored = corpus.raw(game_id)
        if stored.get('summary'):
            continue
        try:
            summary = source.game_summary(fetcher, game_id)
        except source.SourceError as error:
            missing += 1
            log(f'no listing record for {game_id}: {error}')
            continue
        corpus.store(game_id, stored['data'], summary)
        completed += 1
        log(f'completed {game_id}')
    return completed, missing


@dataclass(frozen=True)
class SyncReport:
    scanned: int
    added: int
    skipped: int
    rejected: tuple[tuple[str, str], ...]
    exhausted: bool

    def describe(self) -> str:
        tail = ' (listing exhausted)' if self.exhausted else ''
        return (f'scanned {self.scanned} listed games, added {self.added}, '
                f'already had {self.skipped}, rejected {len(self.rejected)}{tail}')


def sync(corpus: Corpus, fetcher: source.Fetcher, *, wanted: int, max_pages: int = 200,
         start: int = 0, players: int | None = None, lost_fleet: bool | None = None,
         log=lambda message: None) -> SyncReport:
    """Page the ended-game listing until `wanted` new Gaia Project games are mirrored.

    The listing interleaves every boardgame on the site, so most scanned entries are
    skipped. Pages are walked forward from `start`, which is an offset into the listing
    rather than a page number. `start` matters: the listing runs newest first, and Gaia
    Project is a much smaller share of recent games than of older ones, so a crawl aimed
    at volume should begin deeper in. `players` and `lost_fleet` narrow the crawl using
    the listing alone, so a game of the wrong setup costs one listing row and no download.
    """
    if wanted < 0 or max_pages < 1 or start < 0:
        raise ValueError('Invalid sync window')
    scanned = added = skipped = 0
    rejected: list[tuple[str, str]] = []
    exhausted = False
    for page_number in range(max_pages):
        if added >= wanted:
            break
        page = source.ended_page(fetcher, skip=start + page_number * source.PAGE_LIMIT)
        if not page:
            exhausted = True
            break
        for summary in page:
            if added >= wanted:
                break
            if not source.is_wanted(summary, players=players, lost_fleet=lost_fleet):
                continue
            scanned += 1
            game_id = summary['_id']
            if game_id in corpus:
                skipped += 1
                continue
            data = source.gameplay_data(fetcher, game_id)
            try:
                corpus.store(game_id, data, summary)
            except RecordError as error:
                rejected.append((game_id, str(error)))
                log(f'rejected {game_id}: {error}')
                continue
            added += 1
            log(f'added {game_id} ({added}/{wanted})')
    return SyncReport(scanned, added, skipped, tuple(rejected), exhausted)
