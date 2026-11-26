import glob
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
            sys.path.insert(0, HERE)
            import mark_sheet as ms
            self.assertEqual(data["board"], os.path.basename(ms.BOARD_IMG))
            raw = ms.build_data(glob.glob(os.path.join(td, "x-pair-*.json.gz")))
            self.assertEqual(raw["board"], ms.BOARD_IMG)
            self.assertIn(ms.BOARD_IMG, ms.asset_files(raw))
            if os.path.isfile(os.path.join(ms.ASSET_ROOT, ms.BOARD_IMG)):
                self.assertIn(os.path.basename(ms.BOARD_IMG), files)
            self.assertIn("guide", raw)
            self.assertEqual(set(ms.FACTION_GUIDE), set(ms.FACTION_KO))
            for f in ms.FACTION_GUIDE:
                self.assertIn(f, ms.FACTION_KO)
                self.assertEqual(len(ms.FACTION_GUIDE[f]), 2)
            self.assertNotIn("종족 가까운", html)
            self.assertNotIn('class":"sec"', html)
            self.assertNotIn('"class":"sec"', html)


class ShipFedTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, HERE)
        import mark_sheet
        self.ms = mark_sheet

    def panel(self, boards, fed, t5):
        st = {"players": [{"player_id": 0, "faction": "Nevlas"}], "turn_order": [0],
              "research_board": {"federation_tokens": fed, "terraforming_level_5_token": t5},
              "spaceship_boards": boards}
        return self.ms.game_start_panel(st)

    def test_synthetic(self):
        p = self.panel([{"id": "Twilight", "tech_tiles": [], "federation_token": 9, "artifact_pool": [4, 10]},
                        {"id": "Rebellion", "tech_tiles": [11, 11, 11, 11], "federation_token": 11,
                         "artifact_pool": []}], [1, 7, 1, 2], 4)
        for k in ("ship_tech", "ship_fed", "ship_art", "fed_supply"):
            self.assertIn(k, p)
        self.assertEqual([e[3] for e in p["ship_tech"]], ["리벨리온"])
        self.assertTrue(p["ship_tech"][0][1].startswith("tech_tiles/rendered/std_11_"))
        self.assertEqual(len(p["ship_art"]), 2)
        self.assertTrue(p["ship_art"][0][1].startswith("artifacts/normalized/artifact_04_"))
        self.assertTrue(p["ship_fed"][0][1].startswith("federation_tokens_lost_fleet/normalized/fed_09_"))
        self.assertEqual([e[0] for e in p["fed_supply"]], [4])
        self.assertEqual(p["fed_supply"][0][3], "테라 5단계")

    def test_real_first_replay(self):
        paths = sorted(glob.glob(os.path.expanduser(
            "~/gaia-media/ai-replays/ab-lab-138-setup-placement-sim-20-pair-*.json.gz")))
        if not paths:
            self.skipTest("no replays")
        g = self.ms.load_game(paths[0])["start"]
        self.assertTrue(g["fed_supply"])
        with gzip.open(paths[0], "rt") as f:
            has = bool(json.load(f)["frames"][0]["state"].get("spaceship_boards"))
        if has:
            self.assertTrue(g["ship_fed"])
            self.assertTrue(g["ship_art"])
            self.assertTrue(g["ship_tech"])


if __name__ == "__main__":
    unittest.main()
