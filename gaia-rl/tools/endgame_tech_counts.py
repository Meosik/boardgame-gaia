"""Advanced Tech tiles and level-5 research tracks per seat at the end of lab/teacher_ab games.

User 2026-10-19 "교사들은 고급기술이나 5단계를 얼마나 많이 올리나?": each game is replayed from its seed with
the logged decisions (no per-step snapshot) and the end state is read per seat: Advanced Tech tiles
held (the Lost Fleet extra tile included), tracks at level 5, tracks at level 4+, final VP.
Only complete games count; use 6-round runs for the whole-game picture.

  .venv/bin/python tools/endgame_tech_counts.py ~/projects/gaia-lab/gaia-rl/runs --glob 'lab-*-full'
"""
import argparse
import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'tools')]

TRACKS = ('terraforming', 'navigation', 'ai', 'gaia', 'economy', 'science')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('runs', type=Path)
    parser.add_argument('--glob', default='lab-*-full')
    args = parser.parse_args()
    from gaia_rl import Environment
    rows = defaultdict(lambda: defaultdict(float))
    games = skipped = 0
    for run in sorted(args.runs.expanduser().glob(args.glob)):
        for game_dir in sorted(run.glob('pair-*/game-*')):
            result_file = game_dir/'result.json'
            if not result_file.exists():
                continue
            result = json.loads(result_file.read_text())
            if not result.get('complete'):
                continue
            env = Environment(result['seed'], 2000)
            try:
                with gzip.open(game_dir/'decisions.jsonl.gz', 'rt') as f:
                    for line in f:
                        row = json.loads(line)
                        env.step(row['decision_id'], row['index'])
            except Exception:
                skipped += 1      # the log no longer replays on this engine
                continue
            state = json.loads(env.snapshot_json())['state']
            games += 1
            for seat, player in enumerate(state['players']):
                arm = 'A' if seat in result.get('a_seats', []) else 'B'
                for key in ((arm, player['faction']), ('all', player['faction']), ('all', 'ALL')):
                    r = rows[key]
                    levels = [player['research_tracks'][t] for t in TRACKS]
                    r['seats'] += 1
                    r['advanced'] += len(player.get('advanced_tech_tiles', []))
                    r['level5'] += sum(level >= 5 for level in levels)
                    r['level4'] += sum(level >= 4 for level in levels)
                    r['vp'] += player['vp']
                    # Federation tokens held, green and flipped (the Gleens' own token counts too).
                    r['feds'] += len(player.get('federation_tokens', [])) + len(player.get('gray_federation_tokens', []))
                    r['green_left'] += len(player.get('federation_tokens', []))
                    r['any_advanced'] += bool(player.get('advanced_tech_tiles'))
                    r['any_level5'] += any(level >= 5 for level in levels)
    print(f'games {games} (skipped {skipped} that no longer replay); per seat-game means; '
          f'VP is before final scoring (the log ends at the last decision)')
    print(f"{'':22s}{'seats':>6}{'adv':>6}{'adv>0':>7}{'lvl5':>6}{'lvl5>0':>7}{'lvl4+':>7}{'feds':>6}{'green':>6}{'VP':>7}")
    for key in sorted(rows, key=lambda k: (k[0] != 'all', k[0], k[1] != 'ALL', k[1])):
        r = rows[key]
        n = r['seats']
        print(f"{key[0]+' '+key[1]:22s}{int(n):>6}{r['advanced']/n:>6.2f}{r['any_advanced']/n:>7.0%}"
              f"{r['level5']/n:>6.2f}{r['any_level5']/n:>7.0%}{r['level4']/n:>7.2f}"
              f"{r['feds']/n:>6.2f}{r['green_left']/n:>6.2f}{r['vp']/n:>7.1f}")


if __name__ == '__main__':
    main()
