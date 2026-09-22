"""Command line: mirror recorded games, then turn the mirror into rows or a report.

    python -m bgs_records census   [--limit 5000]         # what setups exist at all
    python -m bgs_records fetch    --wanted 300 [--start 30000]
    python -m bgs_records backfill                       # ratings for older mirror entries
    python -m bgs_records report   [--min-elo 150] [--json report.json]
    python -m bgs_records build    --out decisions.jsonl [--min-elo 150]

`report` and `build` select four-player Lost Fleet games, widen to four-player base game
when too few carry the expansion, and drop any game with a seat below the rating floor.
"""
import argparse
import json
from pathlib import Path
import sys

from . import catalog as catalog_module
from . import census, dataset, selection, source
from .corpus import Corpus, backfill_summaries, sync
from .timeline import RecordError

#: Resolved from this file, not the working directory, so the default is the same
#: mirror wherever the command is run from.
DEFAULT_CORPUS = Path(__file__).resolve().parents[2] / 'research/bgs-records'


def _corpus(args) -> Corpus:
    return Corpus(Path(args.corpus))


def _selected(corpus: Corpus, args) -> selection.Selection:
    """Choose from the index alone — no game is rebuilt to decide whether to use it."""
    return selection.select(corpus.entries(), players=args.players, min_elo=args.min_elo,
                            require_all_seats=args.all_seats_rated,
                            allow_fallback=not args.strict_expansion)


def _fetch(args) -> int:
    corpus = _corpus(args)
    fetcher = source.Fetcher(min_interval=args.interval)
    print(f'{source.ended_count(fetcher)} finished games listed site-wide '
          f'(all boardgames); starting at offset {args.start}', file=sys.stderr)
    report = sync(corpus, fetcher, wanted=args.wanted, max_pages=args.max_pages,
                  start=args.start, players=args.only_players,
                  lost_fleet=True if args.only_lost_fleet else None,
                  log=lambda message: print(message, file=sys.stderr))
    print(report.describe())
    for game_id, reason in report.rejected:
        print(f'  rejected {game_id}: {reason}', file=sys.stderr)
    print(f'corpus now holds {len(corpus)} games at {corpus.root}')
    return 0


def _census(args) -> int:
    counted = census.take(source.Fetcher(min_interval=args.interval), start=args.start,
                          limit=args.limit,
                          log=lambda message: print(message, file=sys.stderr))
    print(counted.describe())
    print(f'\nfour-player: {counted.count(players=4)}   '
          f'lost-fleet: {counted.count(expansion="lost-fleet")}   '
          f'four-player lost-fleet: '
          f'{sum(t for (p, e), t in counted.setups.items() if p == 4 and "lost-fleet" in e)}')
    if args.json:
        Path(args.json).write_text(json.dumps({
            'listed': counted.listed, 'scanned': counted.scanned, 'gaia': counted.gaia,
            'setups': {f'{p}p|{"+".join(e)}': t for (p, e), t in counted.setups.items()},
            'expansion_games': [list(g) for g in counted.expansion_games],
        }, indent=1, sort_keys=True))
        print(f'wrote {args.json}')
    return 0


def _reindex(args) -> int:
    corpus = _corpus(args)
    rebuilt = corpus.reindex()
    print(f'rewrote {rebuilt} of {len(corpus)} index entries')
    return 0


def _backfill(args) -> int:
    corpus = _corpus(args)
    done, missing = backfill_summaries(
        corpus, source.Fetcher(min_interval=args.interval),
        log=lambda message: print(message, file=sys.stderr))
    print(f'completed {done} games, {missing} still without a listing record '
          f'(those cannot be rating-filtered)')
    return 0


def _report(args) -> int:
    corpus = _corpus(args)
    chosen = _selected(corpus, args)
    print(chosen.describe())
    print()
    if not chosen.game_ids:
        print('No mirrored game matches those filters.', file=sys.stderr)
        return 1
    floor = args.min_elo or 0
    unreadable = []

    def stream():
        for game_id in chosen.game_ids:
            try:
                yield corpus.record(game_id)
            except RecordError as error:
                unreadable.append((game_id, str(error)))

    built = catalog_module.build(
        stream(),
        seat_filter=None if not floor
        else lambda record: selection.qualifying_seats(record, floor))
    print(catalog_module.summarise(built))
    if unreadable:
        print(f'\n{len(unreadable)} selected games could not be read:')
        for game_id, reason in unreadable[:10]:
            print(f'  {game_id}: {reason}')
    if args.json:
        Path(args.json).write_text(json.dumps(built.as_dict(), indent=1, sort_keys=True))
        print(f'\nwrote {args.json}')
    return 0


def _build(args) -> int:
    corpus = _corpus(args)
    chosen = _selected(corpus, args)
    print(chosen.describe())
    wanted = set(chosen.game_ids)
    if not wanted:
        print('No mirrored game matches those filters.', file=sys.stderr)
        return 1

    report = dataset.write(corpus, Path(args.out), game_ids=wanted,
                           include_setup_round=not args.skip_setup,
                           include_reactions=args.include_reactions,
                           min_elo=args.min_elo or None)
    print(report.describe())
    # Say which selected games no longer read, rather than quietly shipping a smaller
    # dataset than the selection suggests.
    for game_id, reason in report.unreadable:
        print(f'  excluded {game_id}: {reason}', file=sys.stderr)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='bgs_records', description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--corpus', default=DEFAULT_CORPUS, type=Path,
                        help=f'directory holding the mirrored games (default: {DEFAULT_CORPUS})')
    filters = argparse.ArgumentParser(add_help=False)
    filters.add_argument('--players', type=int, choices=(2, 3, 4, 5), default=4,
                         help='player count to select (default: 4)')
    filters.add_argument('--min-elo', type=int, default=selection.DEFAULT_MIN_ELO,
                         help='learn only from seats that carried at least this rating '
                              f'into the game (default: {selection.DEFAULT_MIN_ELO}; 0 '
                              'disables). Filters seat by seat: a beginner at the table '
                              'costs their own rows, not the whole game. Unrated seats '
                              'never qualify.')
    filters.add_argument('--all-seats-rated', action='store_true',
                         help='stricter: keep only games where every seat clears the floor')
    filters.add_argument('--strict-expansion', action='store_true',
                         help='never widen to base game, even when almost no Lost Fleet '
                              'games match')
    commands = parser.add_subparsers(dest='command', required=True)

    fetch = commands.add_parser('fetch', help='mirror more finished games')
    fetch.add_argument('--wanted', type=int, default=100,
                       help='how many new games to add before stopping')
    fetch.add_argument('--max-pages', type=int, default=200)
    fetch.add_argument('--start', type=int, default=0,
                       help='offset into the listing to start from; the newest games are '
                            'a much smaller share of Gaia Project than the older ones')
    fetch.add_argument('--interval', type=float, default=0.25,
                       help='minimum seconds between requests')
    fetch.add_argument('--only-players', type=int, choices=(2, 3, 4, 5),
                       help='download only games with this many players; the listing '
                            'already says, so the rest cost nothing')
    fetch.add_argument('--only-lost-fleet', action='store_true',
                       help='download only Lost Fleet games')
    fetch.set_defaults(handler=_fetch)

    survey = commands.add_parser(
        'census', help='count what setups the archive holds, from the listing alone')
    survey.add_argument('--interval', type=float, default=0.12)
    survey.add_argument('--start', type=int, default=0)
    survey.add_argument('--limit', type=int,
                        help='read only this many listing entries (default: all of them)')
    survey.add_argument('--json', help='also write the tally here')
    survey.set_defaults(handler=_census)

    refresh = commands.add_parser(
        'reindex', help='rewrite index entries from the mirrored files (no network)')
    refresh.set_defaults(handler=_reindex)

    complete = commands.add_parser(
        'backfill', help='fetch the listing record (ratings) for games mirrored without one')
    complete.add_argument('--interval', type=float, default=0.25)
    complete.set_defaults(handler=_backfill)

    report = commands.add_parser('report', parents=[filters],
                                 help='counted observations over the mirror')
    report.add_argument('--json', help='also write the full catalog here')
    report.set_defaults(handler=_report)

    build = commands.add_parser('build', parents=[filters],
                                help='write decision rows as JSONL')
    build.add_argument('--out', required=True)
    build.add_argument('--skip-setup', action='store_true',
                       help='drop the pre-round-1 placement and booster choices')
    build.add_argument('--include-reactions', action='store_true',
                       help='also emit charge/decline/income bookkeeping moves')
    build.set_defaults(handler=_build)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == '__main__':
    raise SystemExit(main())
