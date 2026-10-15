"""explain_decision with some guide flags left off: which rule moved a score.

  .venv/bin/python tools/explain_without.py <game_dir> --step N --spec <spec> --off flag [flag ...]
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]

import teacher_patches as tp  # noqa: E402
from explain_decision import explain  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('game_dir', type=Path)
    parser.add_argument('--step', type=int, required=True)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--off', nargs='+', default=[])
    parser.add_argument('--top', type=int, default=8)
    parser.add_argument('--comparisons', type=int, default=0)
    args = parser.parse_args()
    off = set(args.off)
    inner = tp._guide.__setitem__

    class Guide(dict):
        def __setitem__(self, key, value):
            inner(key, False if key in off else value)
    guide = Guide(tp._guide)
    inner = dict.__setitem__.__get__(guide)
    tp._guide = guide
    print(explain(args.game_dir.expanduser(), args.step, args.top, args.spec, args.comparisons))


if __name__ == '__main__':
    main()
