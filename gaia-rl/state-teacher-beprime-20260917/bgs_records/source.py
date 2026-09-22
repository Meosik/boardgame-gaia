"""Read-only public boardgamers.space access: ended games only, no credentials, no writes.

Four endpoints carry everything this package needs, all of them public, so nothing here
ever sends a session cookie:

    /game/status/ended          pages over finished games of every boardgame, newest first
    /game/status/ended/count    how many there are in total — it ignores any filter
    /gameplay/<id>/data         one game's engine state: `moveHistory` and `advancedLog`
    /game/<id>                  one game's listing record: placements and ratings

The split matters. Play and ratings live on different endpoints, and a listing entry
marked `ended` may be a game somebody abandoned in round two — only the gameplay record's
own `ended` flag distinguishes them.
"""
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://www.boardgamers.space/api'
USER_AGENT = 'gaia-rl-bgs-records/1 (+offline Gaia Project research)'
GAME_NAME = 'gaia-project'
PAGE_LIMIT = 50  # The endpoint silently caps a larger `count`, so never ask for more.


class SourceError(RuntimeError):
    """The site answered, but not with a record this package is willing to trust."""


def _open(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        url, headers={'User-Agent': USER_AGENT, 'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
        if response.headers.get('Content-Encoding') == 'gzip':
            payload = gzip.decompress(payload)
        return payload


class Fetcher:
    """Paces and retries requests. `transport` is injected so tests never touch the network."""

    def __init__(self, transport=_open, *, min_interval: float = 0.25,
                 timeout: float = 40.0, attempts: int = 4, sleep=time.sleep,
                 clock=time.monotonic):
        if min_interval < 0 or timeout <= 0 or attempts < 1:
            raise ValueError('Invalid fetcher pacing')
        self._transport = transport
        self._min_interval = min_interval
        self._timeout = timeout
        self._attempts = attempts
        self._sleep = sleep
        self._clock = clock
        self._last = None
        self.requests = 0

    def _wait(self) -> None:
        if self._last is not None:
            remaining = self._min_interval - (self._clock() - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()

    def json(self, path: str):
        if not path.startswith('/'):
            raise ValueError(f'Path must be absolute: {path!r}')
        url = BASE + path
        for attempt in range(1, self._attempts + 1):
            self._wait()
            self.requests += 1
            try:
                payload = self._transport(url, self._timeout)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
                if attempt == self._attempts:
                    raise SourceError(f'{url} unreachable after {attempt} attempts: {error}')
                self._sleep(min(2.0 ** attempt, 30.0))
                continue
            try:
                return json.loads(payload)
            except json.JSONDecodeError as error:
                raise SourceError(f'{url} did not return JSON: {error}')
        raise AssertionError('unreachable')


def ended_page(fetcher: Fetcher, skip: int, count: int = PAGE_LIMIT) -> list[dict]:
    """One page of finished games across all boardgames, newest first."""
    if skip < 0 or not 1 <= count <= PAGE_LIMIT:
        raise ValueError('Invalid page window')
    page = fetcher.json(f'/game/status/ended?count={count}&skip={skip}')
    if not isinstance(page, list):
        raise SourceError('Ended-game listing is not a list')
    for summary in page:
        if not isinstance(summary, dict) or not isinstance(summary.get('_id'), str):
            raise SourceError('Ended-game listing entry has no id')
    return page


def ended_count(fetcher: Fetcher) -> int:
    """How many finished games the site holds, across every boardgame it hosts.

    There is no per-boardgame count: the endpoint ignores a filter and answers with the
    archive total, so a Gaia Project figure has to be estimated by sampling the listing.
    """
    total = fetcher.json('/game/status/ended/count')
    if not isinstance(total, int) or total < 0:
        raise SourceError(f'Ended-game count is {total!r}')
    return total


def is_wanted(summary: dict, *, players: int | None = None,
              lost_fleet: bool | None = None) -> bool:
    """A finished, uncancelled Gaia Project game, optionally of one setup only.

    The listing already states the player count and expansions, so a crawl can skip a
    game before paying for its gameplay record. Two-player games are most of the archive
    and downloading them to throw them away is the bulk of a wasted crawl.
    """
    game = summary.get('game') or {}
    if (game.get('name') != GAME_NAME or summary.get('status') != 'ended'
            or summary.get('cancelled')):
        return False
    if players is not None and len(summary.get('players') or ()) != players:
        return False
    if lost_fleet is not None:
        has = 'lost-fleet' in (game.get('expansions') or ())
        if has != lost_fleet:
            return False
    return True


def _check_id(game_id: str) -> None:
    if not game_id or '/' in game_id or '?' in game_id:
        raise ValueError(f'Unusable game id: {game_id!r}')


def game_summary(fetcher: Fetcher, game_id: str) -> dict:
    """One finished game's listing record: final placements and rating changes.

    The gameplay endpoint has the play but no ratings, and the listing has the ratings
    but only page by page. This fetches the listing half for a single game, so a mirror
    built without it can be completed without re-paging the whole archive.
    """
    _check_id(game_id)
    summary = fetcher.json(f'/game/{urllib.parse.quote(game_id)}')
    if not isinstance(summary, dict) or summary.get('_id') != game_id:
        raise SourceError(f'{game_id}: listing record is missing or for another game')
    return summary


def gameplay_data(fetcher: Fetcher, game_id: str) -> dict:
    """One finished game's engine state, including `moveHistory` and `advancedLog`."""
    _check_id(game_id)
    data = fetcher.json(f'/gameplay/{urllib.parse.quote(game_id)}/data')
    if not isinstance(data, dict):
        raise SourceError(f'{game_id}: gameplay data is not an object')
    return data
