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


WHEEL = ["Volcanic", "Oxide", "Swamp", "Ice", "Terra", "Titanium", "Desert"]


def fake(path, factions):
    hexes = {"0,0": {"planet": {"planet_type": "Terra"}, "structure": "x"},
             "1,0": {"planet": None}, "0,1": {"planet": {"planet_type": "Gaia"}}}
    hexes["9,9"] = {"planet": {"planet_type": "Asteroid"}}
    hexes["10,9"] = {"planet": None}
    hexes["9,10"] = {"planet": None}
    hexes["20,0"] = {"planet": None}  # interspace hole
    state = {"terraforming_color_order": WHEEL,
             "board": {"hexes": hexes, "spaceship_tiles": {"Eclipse": {"q": 20, "r": 0}},
                       "sectors": [{"id": 1, "rotation": 0, "origin": "0,0"},
                                   {"id": 11, "rotation": 0, "origin": "9,9"}]},
             "players": [{"player_id": i, "faction": f} for i, f in enumerate(factions)],
             "turn_order": [2, 0, 1, 3],
             "round_tiles": [{"id": i, "condition": "x", "vp_per_unit": 2} for i in (3, 10, 11, 6, 1, 2)],
             "final_scoring_tiles": [{"id": 3}, {"id": 6}],
             "boosters": [5, 10, 14, 7, 9, 4, 2],
             "research_board": {"tech_tile_slots": [2, 3, 4, 10, 7, 9, 5, 8, 6],
                                "advanced_tech_tiles": [5, 17, 19, 12, 8, 22]}}
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
            self.assertIn('id="main"', html)
            files = sorted(os.listdir(os.path.join(td, "mark-assets")))
            self.assertIn("01.webp", files)
            self.assertIn("11-2.webp", files)  # Asteroid-only layout = side B
            self.assertTrue(any(f.startswith("interspace_02") for f in files))
            sec = {s[0]: s for s in data["games"][0]["sectors"]}
            self.assertEqual(sec[11][4], "11-2.webp")
            self.assertEqual(sec[1][4], "01.webp")
            st = data["games"][0]["start"]
            for k in ("rounds", "final", "boosters", "std", "adv", "seats"):
                self.assertIn(k, st)
            self.assertEqual(len(st["rounds"]), 6)
            self.assertEqual(len(st["seats"]), 4)
            self.assertEqual(st["seats"], ["Terrans", "Nevlas", "Firaks", "Ivits"])
            # engine id 10 uses image 11 and vice versa; ids stay engine ids
            r = {e[0]: e[1] for e in st["rounds"]}
            self.assertTrue(r[10].startswith("round_11_"))
            self.assertTrue(r[11].startswith("round_10_"))
            self.assertTrue(r[3].startswith("round_03_"))
            self.assertEqual(len(st["std"]), 9)
            self.assertEqual(len(st["adv"]), 6)
            self.assertEqual(len(st["boosters"]), 7)
            self.assertTrue(any(f.startswith("round_11_") for f in files))
            # faction mark colours: every faction has a home planet that the JS PC table knows
            pc = re.search(r"var PC=\{(.*?)\};", html, re.S).group(1)
            pc_keys = set(re.findall(r"(\w+):\"#", pc))
            for g in data["games"]:
                for f in g["factions"]:
                    if f == "Zzz":
                        continue  # fake unknown faction: falls back to the FC palette
                    self.assertIn(data["home"].get(f), pc_keys, f)
            for f in data["ko"]:
                self.assertIn(data["home"].get(f), pc_keys, f)
            self.assertEqual(len(st["close"]), 6)
            self.assertIn("종족 가까운 정도 (테라포밍 단계)", html)
            ds = [c[2] for c in st["close"]]
            self.assertEqual(ds, sorted(ds))
            self.assertNotIn('class":"sec"', html)
            self.assertNotIn('"class":"sec"', html)


class WheelTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, HERE)
        import mark_sheet
        self.ms = mark_sheet

    def test_distance(self):
        d = self.ms.wheel_distance
        ring = self.ms.PLANET_RING
        self.assertEqual(d(ring, "Terra", "Oxide"), 1)
        self.assertEqual(d(ring, "Terra", "Desert"), 3)
        self.assertEqual(d(ring, "Titanium", "Terra"), 2)
        self.assertEqual(d(ring, "Terra", "Terra"), 0)
        self.assertIsNone(d(ring, "Asteroid", "Terra"))

    def test_pairs(self):
        c = self.ms.faction_closeness(self.ms.PLANET_RING, ["Geodens", "Nevlas", "Xenos", "Tinkeroids"])
        self.assertEqual(len(c), 6)
        self.assertEqual([x[2] for x in c if x[2] is None], [None] * 3)
        self.assertIsNone(c[-1][2])
        self.assertEqual(c[0][2], 1)


if __name__ == "__main__":
    unittest.main()
