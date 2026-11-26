import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "mark_sheet.py")


def fake(path, factions):
    hexes = {"0,0": {"planet": {"planet_type": "Terra"}, "structure": "x"},
             "1,0": {"planet": None}, "0,1": {"planet": {"planet_type": "Gaia"}}}
    hexes["9,9"] = {"planet": {"planet_type": "Asteroid"}}
    hexes["10,9"] = {"planet": None}
    hexes["9,10"] = {"planet": None}
    hexes["20,0"] = {"planet": None}  # interspace hole
    state = {"board": {"hexes": hexes, "spaceship_tiles": {"Eclipse": {"q": 20, "r": 0}},
                       "sectors": [{"id": 1, "rotation": 0, "origin": "0,0"},
                                   {"id": 11, "rotation": 0, "origin": "9,9"}]},
             "players": [{"player_id": i, "faction": f} for i, f in enumerate(factions)]}
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump({"frames": [{"state": state}]}, f)


class MarkSheetTest(unittest.TestCase):
    def test_generate(self):
        with tempfile.TemporaryDirectory() as td:
            fake(os.path.join(td, "x-pair-003-game-0.json.gz"), ["Nevlas", "Firaks", "Terrans", "Ivits"])
            fake(os.path.join(td, "x-pair-007-game-0.json.gz"), ["Lantids", "Xenos", "Gleens", "Zzz"])
            out = os.path.join(td, "o.html")
            subprocess.run([sys.executable, "-I", SCRIPT, "--replays", os.path.join(td, "x-pair-*.json.gz"),
                            "--out", out], check=True)
            html = open(out, encoding="utf-8").read()
            for s in ("pair-003", "pair-007", "네블라", "파이락", "하이브", "란티드"):
                self.assertIn(s, html)
            self.assertNotIn("structures", html)
            m = re.search(r"var DATA=(.*?);\nvar PC=", html, re.S)
            data = json.loads(m.group(1))
            self.assertEqual([g["id"] for g in data["games"]], ["pair-003", "pair-007"])
            self.assertEqual(len(data["games"][0]["hexes"]), 7)
            self.assertIn("mark-assets/", html)
            files = sorted(os.listdir(os.path.join(td, "mark-assets")))
            self.assertIn("01.webp", files)
            self.assertIn("11-2.webp", files)  # Asteroid-only layout = side B
            self.assertTrue(any(f.startswith("interspace_02") for f in files))
            sec = {s[0]: s for s in data["games"][0]["sectors"]}
            self.assertEqual(sec[11][4], "11-2.webp")
            self.assertEqual(sec[1][4], "01.webp")


if __name__ == "__main__":
    unittest.main()
