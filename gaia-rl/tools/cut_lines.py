"""Remove line ranges from a file (1-indexed, inclusive, numbered on the file as it is now).

  .venv/bin/python tools/cut_lines.py FILE 200-514 935-950 ...

Ranges must not overlap. Prints the line count before and after. Used for the 2026-10-19 pruning
of teacher_patches.py (HANDOFF: rejected families removed, kept in git history).
"""
import sys
from pathlib import Path


def main():
    path = Path(sys.argv[1])
    ranges = []
    for arg in sys.argv[2:]:
        a, _, b = arg.partition('-')
        a, b = int(a), int(b or a)
        if a < 1 or b < a:
            raise SystemExit(f'bad range {arg}')
        ranges.append((a, b))
    ranges.sort()
    for (a, b), (c, _) in zip(ranges, ranges[1:]):
        if c <= b:
            raise SystemExit(f'overlap {a}-{b} and {c}-')
    lines = path.read_text().splitlines(keepends=True)
    if ranges and ranges[-1][1] > len(lines):
        raise SystemExit(f'{ranges[-1]} beyond {len(lines)} lines')
    drop = {n for a, b in ranges for n in range(a, b+1)}
    kept = [line for n, line in enumerate(lines, 1) if n not in drop]
    path.write_text(''.join(kept))
    print(f'{path}: {len(lines)} -> {len(kept)} lines ({len(drop)} removed)')


if __name__ == '__main__':
    main()
