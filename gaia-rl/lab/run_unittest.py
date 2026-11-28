"""Run tool unit tests with the lab import path (python, frozen baseline teacher, tools): run_unittest.py <module>..."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ('tools', 'baseline-teacher-20260917', 'python'):
    sys.path.insert(0, str(ROOT / sub))
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:])
result = unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
