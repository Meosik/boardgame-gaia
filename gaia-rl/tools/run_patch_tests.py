"""Run tools/test_teacher_patches.py with the paths the lab uses (no PYTHONPATH needed).

  .venv/bin/python tools/run_patch_tests.py [TestClass ...]
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('GAIA_ENGINE_FIXES_2', '1')
sys.path[:0] = [str(ROOT/'python'), str(ROOT/'baseline-teacher-20260917'), str(ROOT/'tools')]

import test_teacher_patches  # noqa: E402

names = [f'test_teacher_patches.{n}' for n in sys.argv[1:]]
loader = unittest.defaultTestLoader
suite = loader.loadTestsFromNames(names) if names else loader.loadTestsFromModule(test_teacher_patches)
sys.exit(not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful())
