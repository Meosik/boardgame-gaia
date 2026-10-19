"""Line-by-line comparison of two text files (a decision trace before and after a code change).

  .venv/bin/python tools/diff_lines.py BEFORE AFTER

Prints the line counts, the number of differing lines and the first few differences; exit code 1
when the files differ. Used with guide_values_smoke.py --output for the no-behaviour-change check
of the 2026-10-19 teacher_patches.py pruning.
"""
import sys
from pathlib import Path


def main():
    a, b = (Path(p).read_text().splitlines() for p in sys.argv[1:3])
    shown, differing = 0, 0
    for n, (x, y) in enumerate(zip(a, b), 1):
        if x != y:
            differing += 1
            if shown < 8:
                print(f'line {n}:\n  before {x}\n  after  {y}')
                shown += 1
    print(f'{len(a)} vs {len(b)} lines, {differing} differing lines in the common part')
    sys.exit(1 if differing or len(a) != len(b) else 0)


if __name__ == '__main__':
    main()
