#!/usr/bin/env python3
"""Generate one self-contained HTML page where the owner taps map hexes to mark
per-faction start hexes and early sites for lab experiment 138 replays.

The page opens with the AI teacher's actual setup placements (structures in the
last replay frame) already marked; the owner only corrects the odd ones, and
the page lists what was changed (removed / added hexes per faction).
"""
import argparse
import glob
import gzip
import json
import os
import re
import shutil

FACTION_KO = {
    "Terrans": "테란", "Lantids": "란티드", "Xenos": "제노스", "Gleens": "글린",
    "Taklons": "타클론", "Ambas": "앰바스", "HadschHallas": "하드쉬 할라",
    "Ivits": "하이브", "Geodens": "기오덴", "BalTaks": "발타크", "Firaks": "파이락",
    "Bescods": "매드 안드로이드", "Nevlas": "네블라", "Itars": "아이타",
    "Moweyds": "모웨이드", "SpaceGiants": "스페이스 자이언트",
    "Tinkeroids": "팅커로이드", "Darkanians": "다카니안",
}
# home planet per faction, from gaia-engine/data/factions.toml (id/home_planet pairs)
FACTION_PLANET = {
    "Terrans": "Terra", "Lantids": "Terra", "Xenos": "Desert", "Gleens": "Desert",
    "Taklons": "Swamp", "Ambas": "Swamp", "HadschHallas": "Oxide", "Ivits": "Oxide",
    "Geodens": "Volcanic", "BalTaks": "Volcanic", "Firaks": "Titanium",
    "Bescods": "Titanium", "Nevlas": "Ice", "Itars": "Ice",
    "Tinkeroids": "Asteroid", "Moweyds": "ProtoPlanet",
    "SpaceGiants": "ProtoPlanet", "Darkanians": "Asteroid",
}

# per-faction [opening, play, tech] guide; opening/play source: SH04 보드라이프 "종족 별 추천 빌드"
# (gaia-rl/research/strategy/claims-new/SH04-SH05.csv); tech line from the conflicts/base-factions.md,
# weak-factions.md, general-and-lf.md decisions (2026-10-20 rulings)
FACTION_GUIDE = {
    "Terrans": ["1순위 연4광·연교2광 / 2순위 의교광광(1R 기술 연방 될 때만)·연2광", "가이아포밍 각, 8토큰이라 유물 각. 가이아 3점 타일은 중반에", "가이아 경쟁 종족 있으면 항해2→가이아, 없으면 과학4 먼저, 테라포밍 안 올림. 4충전 타일(가이아 많이 잡는 판이면 가이아당 3점 타일)"],
    "Lantids": ["1순위 의4광 / 2순위 의교2광 (연방은 그 뒤)", "의회 먼저, 기생. 기생 안 한 광산 2개 남기고 업그레이드 후 연방", "1R 항해 없이 경제2 먼저→항해, 4연방 노리면 항해 정상"],
    "HadschHallas": ["1순위 연4광·연교2광·2연2광 / 2순위 의4광·의교2광(리벨리온 3큐브 될 때) / 3순위 아2광", "의회 전까지 광석 수급 집중", "경제2 먼저(이웃 견제·새 행성 2개 닿으면 항해2), 소행성 닿으면 가이아1. 1광석1충전 타일, 4돈 타일은 뒤로"],
    "Ivits": ["1순위 의연2광·의연1광 / 2순위 의4광·의교2광 / 3순위 의아", "3큐브 액션, 빠른 첫 연방. 유물·가이아포밍 각", "과학 위 고급이 좋거나 5·6R 연구 점수면 과학, 아니면 경제. 1R 1광석+1QIC 타일→큰 건물 4파워 타일"],
    "Geodens": ["1순위 의4광·의교2광 / 2순위 의2광 / 3순위 연4광·연교2광(테라포밍 액션 없을 때)", "의회 먼저, 새 행성 유형 계속", "경제 먼저(땅 경쟁 심하면 테라포밍1). 4충전 vs 4돈 타일 미정, 행성 종류당 지식 타일은 4R 이후"],
    "BalTaks": ["1순위 연4광·연교2광·아2광", "가이아 트랙 먼저. 함선 2거리 타일 최고, 리벨리온 3큐브 중요", "1R 가이아4(안 되면 3→2R 4)→AI·테라포밍. 4충전보다 4돈 타일, +1사거리 타일"],
    "Gleens": ["1순위 연4광·아2광(리벨리온 3큐브 될 때) / 2순위 연교광광", "4돈 수입 타일, 가이아 3점 타일", "항해2에서 멈춤→가이아 종족 있으면 테라포밍, 없으면 가이아. 4돈 타일, 가이아 노선이면 가이아당 3점 타일"],
    "Xenos": ["1순위 연4광·연교2광 / 2순위 의교광(1R 기술 연방 될 때만)", "3큐브 액션·고급 기술 타일 집중, 파워 액션 한 박자 빠르게", "가이아 경쟁 없고 차원 변환 행성 가까우면 가이아, AI는 정상 고급 타일이 강할 때만 일찍"],
    "Ambas": ["1순위 연4광 / 2순위 아광광(빠른 연방, 항해 고급 타일 2R)·연교2광", "4돈 수입·큰 건물 4티어 타일. 의회는 3~4R, 그 전엔 광산", "광산 오프닝이면 항해 먼저(아카데미 오프닝이면 경제·과학), 가이아 비추. 4돈 타일+큰 건물 4파워 타일"],
    "Taklons": ["1순위 연4광 / 2순위 아2광·연교2광", "항해·큐브로 파워 받는 자리. 4파워 회전 타일 최고", "항해로 충전 받을 자리 확보. 4충전 타일(가이아 밑이면 1지식1돈 타일)"],
    "Firaks": ["1순위 의교(사실상 의연) / 2순위 연교2광(2R 의회)", "트와일라잇 2광석3파워→연구소. 경제 트랙", "경제2→(이웃 많거나 땅 경쟁이면 항해2)→경제4, 3연방이면 항해5. 다음 테라포밍 vs 가이아 미정, AI는 경제4·테라포밍4 뒤. 1광석1충전·4충전 타일, 4돈 타일 피함"],
    "Bescods": ["1순위 연4광·2연2광·연교2광 / 2순위 의교(1R 기술 연방 될 때만)", "회색 행성 확보. 지식은 이미 올린 트랙에", "아이타·네블라·앰바스·타클론 있으면 항해 먼저, 없으면 과학. 고급은 연구소당 3점"],
    "Nevlas": ["1순위 의교2광·의연2광 / 2순위 연교2광·의연", "파워 받는 땅. 4파워 액션, 3그릇 2토큰 유물", "과학 위 고급이 좋거나 5·6R 연구 점수면 과학3, 아니면 경제→테라포밍. 4충전 타일(가이아 밑이면 1광석1충전)"],
    "Itars": ["1순위 아광광(지식 아카데미, 경제)·의교광광(가이아 구역 8토큰+) / 2순위 연교광광", "의회 시작이면 가이아 트랙, 아카데미 시작이면 경제 트랙", "아카데미 시작이면 경제, 의회 시작이면 가이아1→가이아5(발타크 있으면 가이아1까지). 4돈·1광석1충전 타일"],
    "Moweyds": ["1순위 연4광·연교2광·의교·의교광·의연 / 2순위 의광광(기술 연방 될 때)", "티에프마스 능력, 8토큰 유물, 가이아포밍", "연구소 시작이면 항해2→가이아·AI+가이아당 3점 타일, 의회 시작이면 과학·AI"],
    "SpaceGiants": ["1순위 의교2광·의연광 / 2순위 의4광·의연2광", "8토큰 유물, 가이아포밍, 2테라포밍 액션", "항해·가이아 1칸→지식으로 테라포밍 정상. 2테라포밍 광산 타일"],
    "Tinkeroids": ["1순위 의교2광·의연2광 / 2순위 의4광", "1R엔 1테라포밍 능력, 티에프마스 위치, 빠른 연방", "과학·테라포밍 트랙 위주"],
    "Darkanians": ["1순위 연4광·연교2광 / 2순위 의교광광(의회 후 땅 3개 더)·아광(땅 없을 때)", "티에프마스 위치, 땅 먹는 액션 찾기", "경제2·4, 항해 필수, 거리는 QIC로. 경제 위 고급이 좋으면 선아카데미"],
}

DEFAULT_REPLAYS ="~/gaia-media/ai-replays/ab-lab-138-setup-placement-sim-20-pair-*.json.gz"
DEFAULT_OUT = "~/gaia-media/ai-replays/mark-138.html"


def parse_xy(key):
    q, r = key.split(",")
    return int(q), int(r)


REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSET_ROOT = os.path.join(REPO, "gaia-frontend", "src", "assets")

# Port of gaia-frontend/src/assets/sectorImages.ts (deepSpaceSectorSide) tables.
DS_A = {11: ("Asteroid", None, "ProtoPlanet"), 12: ("ProtoPlanet", None, "Transdim"),
        13: (None, "Asteroid", "Transdim"), 14: (None, "Asteroid", "ProtoPlanet"),
        15: (None, None, "ProtoPlanet"), 16: (None, "ProtoPlanet", None),
        17: (None, None, "Transdim"), 18: (None, None, "ProtoPlanet")}
DS_B = {11: ("Asteroid", None, None), 12: (None, None, "Asteroid"),
        13: (None, "Asteroid", None), 14: (None, "Asteroid", None),
        15: (None, "Asteroid", "ProtoPlanet"), 16: (None, "Asteroid", "Asteroid"),
        17: ("Asteroid", None, None), 18: ("Asteroid", None, None)}
DS_LOCAL = [(0, 0), (1, 0), (0, 1)]
# interspaceTileImages.ts: tile id by kind (files are interspace_NN_*.webp)
SHIP_TILE = {"Eclipse": 2, "TFMars": 3, "Rebellion": 4, "Twilight": 5}
TILE_BLANK, TILE_ASTEROID, TILE_PROTO = 1, 6, 7


def rotate_hex_n(q, r, n):
    for _ in range(((n % 6) + 6) % 6):
        q, r = -r, q + r
    return q, r


def axial_distance(aq, ar, bq, br):
    return max(abs(aq - bq), abs(ar - br), abs((-aq - ar) - (-bq - br)))


def deep_space_side(sid, rotation, oq, orr, planets):
    """Port of deepSpaceSectorSide; planets maps (q,r) -> planet_type or None."""
    side_a, side_b = DS_A.get(sid), DS_B.get(sid)
    if not side_a or not side_b:
        return "A"
    am = bm = ad = bd = 0
    for i, (q, r) in enumerate(DS_LOCAL):
        ea, eb = side_a[i], side_b[i]
        if ea == eb:
            continue
        if ea is not None:
            ad += 1
        if eb is not None:
            bd += 1
        rq, rr = rotate_hex_n(q, r, rotation)
        actual = planets.get((oq + rq, orr + rr))
        if ea is not None and actual == ea:
            am += 1
        if eb is not None and actual == eb:
            bm += 1
    if am > bm:
        return "A"
    if bm > am:
        return "B"
    return "A" if ad <= bd else "B"


def sector_file(sid, side):
    """Path relative to the frontend assets dir, or None."""
    if 1 <= sid <= 10:
        return "space_sectors/normalized/%02d.webp" % sid
    if 11 <= sid <= 18:
        return "deep_space_sectors/normalized/%d-%d.webp" % (sid, 2 if side == "B" else 1)
    return None


def interspace_file(tile_id):
    hits = sorted(glob.glob(os.path.join(ASSET_ROOT, "interspace_tiles", "normalized",
                                         "interspace_%02d_*.webp" % tile_id)))
    return "interspace_tiles/normalized/" + os.path.basename(hits[0]) if hits else None


TRACKS_KO = ["테라포밍", "항해", "AI", "가이아", "경제", "과학"]
# gaia-frontend/src/assets/roundScoringTileImages.ts: engine ids 10/11 have swapped art
ROUND_IMG_ID = {10: 11, 11: 10}


def tile_entry(folder, prefix, tid):
    """[id, path relative to assets or None, caption] for tile image <prefix>_<NN>_<desc>.<ext>."""
    if not isinstance(tid, int):
        return [tid, None, str(tid)]
    hits = sorted(glob.glob(os.path.join(ASSET_ROOT, folder, "%s_%02d_*" % (prefix, tid))))
    if not hits:
        return [tid, None, str(tid)]
    base = os.path.basename(hits[0])
    desc = os.path.splitext(base)[0].split("_", 2)[2].replace("_", " ")
    return [tid, folder + "/" + base, desc]


# gaia-frontend/src/displayNames.ts SPACESHIP_DISPLAY_NAMES
SHIP_KO = {"Twilight": "트와일라잇", "Rebellion": "리벨리온", "TFMars": "T F 마스", "Eclipse": "이클립스"}


def fed_entry(tid):
    """Federation token art as in assets/federationTokenImages.ts: base webp, else Lost Fleet png (id 7: none)."""
    e = tile_entry("federation_tokens/normalized", "fed", tid)
    if e[1] is None:
        e = tile_entry("federation_tokens_lost_fleet/normalized", "fed", tid)
    return e


def tid_of(x):
    return x.get("id") if isinstance(x, dict) else x


BOARD_IMG = "boards/normalized/scoring_board.webp"


def game_start_panel(st):
    rt = [tid_of(t) for t in st.get("round_tiles") or []]
    rounds = [tile_entry("round_scoring_tiles/normalized", "round", ROUND_IMG_ID.get(i, i)) for i in rt]
    for e, i in zip(rounds, rt):
        e[0] = i
    final = [tile_entry("final_scoring_tiles/normalized", "final", tid_of(t))
             for t in st.get("final_scoring_tiles") or []]
    boosters = [tile_entry("round_boosters/normalized", "booster", b) for b in st.get("boosters") or []]
    rb = st.get("research_board") or {}
    std = [tile_entry("tech_tiles/rendered", "std", t) for t in rb.get("tech_tile_slots") or []]
    adv = [tile_entry("tech_tiles/rendered", "adv", t) for t in rb.get("advanced_tech_tiles") or []]
    by_id = {p["player_id"]: p["faction"] for p in st["players"]}
    seats = [by_id.get(pid, str(pid)) for pid in st.get("turn_order") or []]
    ship_tech, ship_fed, ship_art = [], [], []
    for b in st.get("spaceship_boards") or []:
        name = SHIP_KO.get(b.get("id"), str(b.get("id")))
        for t in dict.fromkeys(b.get("tech_tiles") or []):
            ship_tech.append(tile_entry("tech_tiles/rendered", "std", t) + [name])
        if b.get("federation_token") is not None:
            ship_fed.append(fed_entry(b["federation_token"]) + [name])
        for a in b.get("artifact_pool") or []:
            ship_art.append(tile_entry("artifacts/normalized", "artifact", a) + [name])
    fed_supply = []
    if rb.get("terraforming_level_5_token") is not None:
        fed_supply.append(fed_entry(rb["terraforming_level_5_token"]) + ["테라 5단계"])
    return {"rounds": rounds, "final": final, "boosters": boosters, "std": std,
            "adv": adv, "seats": seats, "ship_tech": ship_tech, "ship_fed": ship_fed,
            "ship_art": ship_art, "fed_supply": fed_supply}


def xy_of(c):
    if isinstance(c, dict):
        return c["q"], c["r"]
    return parse_xy(c)


def load_game(path):
    m = re.search(r"pair-(\d+)", os.path.basename(path))
    if not m:
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        d = json.load(f)
    st = d["frames"][0]["state"]
    board = st["board"]
    planets = {}
    for key, h in board["hexes"].items():
        pl = h.get("planet") if isinstance(h, dict) else None
        planets[parse_xy(key)] = pl.get("planet_type") if pl else None
    secs = []
    for s in board.get("sectors", []):
        oq, orr = parse_xy(s["origin"])
        rot = s.get("rotation", 0)
        side = deep_space_side(s["id"], rot, oq, orr, planets) if s["id"] >= 11 else None
        secs.append((s["id"], oq, orr, rot, side))
    # hexes covered by sector art (sectorPrintedHexKeys in GameBoard)
    printed = set()
    for (q, r) in planets:
        for sid, oq, orr, rot, side in secs:
            if sid <= 10 and axial_distance(q, r, oq, orr) <= 2:
                printed.add((q, r))
                break
    for sid, oq, orr, rot, side in secs:
        if sid > 10:
            for (q, r) in DS_LOCAL:
                rq, rr = rotate_hex_n(q, r, rot)
                printed.add((oq + rq, orr + rr))
    ships = {}
    for ship, c in (board.get("spaceship_tiles") or {}).items():
        if c:
            ships[xy_of(c)] = ship
    sectors = []
    for sid, oq, orr, rot, side in secs:
        sectors.append([sid, oq, orr, rot, sector_file(sid, side)])
    hexes = []
    for (q, r), pt in planets.items():
        img = None
        if (q, r) not in printed:  # interspace hole
            if (q, r) in ships:
                tile = SHIP_TILE.get(ships[(q, r)], TILE_BLANK)
            elif pt == "Asteroid":
                tile = TILE_ASTEROID
            elif pt == "ProtoPlanet":
                tile = TILE_PROTO
            else:
                tile = TILE_BLANK
            img = interspace_file(tile)
        # [q, r, planet, interspace image, covered by art]
        covered = 1 if img else 0
        if (q, r) in printed:
            covered = 1 if any(s[4] and ((s[0] <= 10 and axial_distance(q, r, s[1], s[2]) <= 2)
                                         or (s[0] > 10 and (q, r) in deep_hexes(s))) for s in sectors) else 0
        hexes.append([q, r, pt, img, covered])
    hexes.sort(key=lambda x: (x[0], x[1]))
    factions = [p["faction"] for p in st["players"]]
    # teacher's setup placements: structure hexes of each player in the LAST frame
    last = d["frames"][-1]["state"]
    by_hex = {}
    for key, h in (last.get("board", {}).get("hexes") or {}).items():
        for s in (h.get("structures") or []) if isinstance(h, dict) else []:
            by_hex.setdefault(s.get("owner"), set()).add("%d,%d" % xy_of(key))
    ai = {}
    for p in last.get("players") or []:
        keys = set()
        for s in p.get("structures") or []:
            if s.get("hex") is not None:
                keys.add("%d,%d" % xy_of(s["hex"]))
        if not keys:
            keys = by_hex.get(p.get("player_id"), set())
        ai[p.get("faction")] = sorted(keys, key=parse_xy)
    return {"id": "pair-%03d" % int(m.group(1)), "hexes": hexes,
            "sectors": sectors, "factions": factions, "start": game_start_panel(st),
            "ai": {f: ai.get(f, []) for f in factions}}


def deep_hexes(s):
    out = set()
    for (q, r) in DS_LOCAL:
        rq, rr = rotate_hex_n(q, r, s[3])
        out.add((s[1] + rq, s[2] + rr))
    return out


def asset_files(data):
    names = set()
    for g in data["games"]:
        for s in g["sectors"]:
            if s[4]:
                names.add(s[4])
        for h in g["hexes"]:
            if h[3]:
                names.add(h[3])
        for key in START_KEYS:
            for e in g["start"][key]:
                if e[1]:
                    names.add(e[1])
    if data.get("board"):
        names.add(data["board"])
    return sorted(names)


def build_data(paths, prefix="mark-assets/"):
    games = [g for g in (load_game(p) for p in paths) if g]
    games.sort(key=lambda g: g["id"])
    return {"games": games, "ko": FACTION_KO, "home": FACTION_PLANET, "exp": "138", "assets": prefix, "tracks": TRACKS_KO,
            "board": BOARD_IMG, "guide": FACTION_GUIDE}


START_KEYS = ("rounds", "final", "boosters", "std", "adv", "ship_tech", "ship_fed", "ship_art", "fed_supply")
TILE_DIRS = ("round_scoring_tiles/", "final_scoring_tiles/", "round_boosters/", "tech_tiles/",
             "artifacts/", "federation_tokens/", "federation_tokens_lost_fleet/")


def shrink_tile(src, rel, dst, max_w=240):
    """Write a downscaled webp copy of a tile image if PIL is available; True when done."""
    if rel == BOARD_IMG:
        max_w = 200
    elif not rel.startswith(TILE_DIRS):
        return False
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        with Image.open(src) as im:
            if im.width > max_w:
                im = im.resize((max_w, max(1, round(im.height * max_w / im.width))), Image.LANCZOS)
            im.save(dst, "WEBP", quality=80)
        return True
    except Exception:
        return False


def copy_assets(data, dest):
    os.makedirs(dest, exist_ok=True)
    n = 0
    for rel in asset_files(data):
        src = os.path.join(ASSET_ROOT, rel)
        if os.path.isfile(src):
            dst = os.path.join(dest, os.path.basename(rel))
            if not shrink_tile(src, rel, dst):
                shutil.copy2(src, dst)
            n += 1
    return n


def render(data, title, storage_key):
    # asset names are stored by basename in the page (files are copied flat)
    d = json.loads(json.dumps(data))
    if d.get("board"):
        d["board"] = os.path.basename(d["board"])
    for g in d["games"]:
        for s in g["sectors"]:
            s[4] = os.path.basename(s[4]) if s[4] else None
        for h in g["hexes"]:
            h[3] = os.path.basename(h[3]) if h[3] else None
        for key in START_KEYS:
            for e in g["start"][key]:
                e[1] = os.path.basename(e[1]) if e[1] else None
    blob = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")
    sk = json.dumps(storage_key).replace("</", "<\\/")
    return (HTML.replace("__SK__", sk)
            .replace("__TITLE__", title.replace("<", "&lt;"))
            .replace("__DATA__", blob))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replays", default=DEFAULT_REPLAYS)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--assets-out", default=None,
                    help="folder for copied art (default: mark-assets next to --out)")
    ap.add_argument("--title", default="실험 138 초반 위치 표시")
    ap.add_argument("--storage-key", default=None,
                    help="localStorage key (default: <--out basename without ext>-v2)")
    a = ap.parse_args()
    paths = sorted(glob.glob(os.path.expanduser(a.replays)))
    if not paths:
        raise SystemExit("no replays match %s" % a.replays)
    out = os.path.abspath(os.path.expanduser(a.out))
    assets = os.path.abspath(os.path.expanduser(a.assets_out)) if a.assets_out \
        else os.path.join(os.path.dirname(out), "mark-assets")
    prefix = os.path.relpath(assets, os.path.dirname(out)).replace(os.sep, "/") + "/"
    data = build_data(paths, prefix)
    n = copy_assets(data, assets)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data, a.title, a.storage_key
                       or os.path.splitext(os.path.basename(out))[0] + "-v2"))
    print("wrote %s: %d games, %d bytes, %d asset files copied to %s"
          % (out, len(data["games"]), os.path.getsize(out), n, assets))


HTML = r"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
body{margin:0;font-family:sans-serif;background:#111;color:#eee}
#wrap{padding:8px;max-width:1500px;margin:0 auto}
h1{font-size:18px;margin:4px 0}
button,select{font-size:16px;padding:10px 12px;margin:3px;border-radius:8px;border:2px solid #555;background:#222;color:#eee}
button.on{border-width:3px;background:#333;font-weight:bold}
#svg{width:100%;height:auto;background:#0b0b10;touch-action:manipulation;display:block}
.hx{fill:none;stroke:#fff;stroke-opacity:.28;stroke-width:.35;pointer-events:none}
.hit{fill:transparent;cursor:pointer}
.art{pointer-events:none}
.mk{pointer-events:none}
.legend span{display:inline-block;margin:2px 8px 2px 0;font-size:14px}
.legend i{display:inline-block;width:14px;height:14px;border-radius:7px;vertical-align:middle;margin-right:4px;border:1px solid #888}
#ta{width:100%;height:140px;display:none;font-size:12px}
#cnt{margin:4px;font-size:15px}
#start{margin:4px 0;font-size:12px}
#start .row{display:flex;flex-wrap:wrap;gap:4px;align-items:flex-start;margin:3px 0}
#start .lab{width:100%;font-weight:bold;color:#9ab}
#start .t{width:48px;text-align:center;line-height:1.15;color:#ccc;font-size:10px}
#start .t img{width:48px;height:auto;display:block;border-radius:4px}
#main{display:flex;flex-direction:row;gap:6px;align-items:flex-start}
#main #start{flex:0 0 38%;max-height:calc(100vh - 150px);overflow-y:auto;margin:0;box-sizing:border-box}
#main #svg{flex:1 1 auto;min-width:0;width:100%;height:auto;max-height:100vh}
#start .t b{display:block;color:#fc6}
#start .seats{font-size:14px}
</style></head><body><div id="wrap">
<h1>__TITLE__</h1>
<div style="font-size:14px;color:#fc6;margin:2px 0">AI가 둔 시작 자리가 찍혀 있습니다. 이상한 것만 탭해서 빼거나 옮기세요.</div>
<div id="games"></div>
<div id="facs"></div>
<div id="kinds"></div>
<div id="main"><div id="start"></div>
<svg id="svg" xmlns="http://www.w3.org/2000/svg"></svg></div>
<div class="legend" id="legend"></div>
<div id="cnt"></div>
<div><button id="copy">결과 복사</button><button id="clear">이 판 되돌리기</button></div>
<div style="font-size:13px;margin:4px 0">바뀐 것</div>
<pre id="chg" style="font-size:12px;white-space:pre-wrap;margin:0 0 8px;color:#cde"></pre>
<textarea id="ta" readonly></textarea>
<script>
var DATA=__DATA__;
var PC={Terra:"#2e6fd8",Volcanic:"#e8862a",Oxide:"#c0392b",Desert:"#f1c40f",Swamp:"#7a5230",Titanium:"#8a8a8a",Ice:"#f4f6f7",Gaia:"#27ae60",Transdim:"#8e44ad",Asteroid:"#5d6d7e",ProtoPlanet:"#a3e4a1",LostPlanet:"#000"};
var PK={Terra:"테란=파랑",Volcanic:"화산=주황",Oxide:"산화=빨강",Desert:"사막=노랑",Swamp:"늪=갈색",Titanium:"티타늄=회색",Ice:"얼음=흰색",Gaia:"가이아=초록",Transdim:"차원 변환=보라",Asteroid:"소행성",ProtoPlanet:"원시 행성"};
var FC=["#00e5ff","#ff2bd6","#aaff00","#ff5a36"];
function fcol(f,i){return PC[DATA.home[f]]||FC[i%4]}
var SK=__SK__;
var store={};try{store=JSON.parse(localStorage.getItem(SK)||"{}")}catch(e){store={}}
var gi=0,fi=0,kind="start";
function save(){try{localStorage.setItem(SK,JSON.stringify(store))}catch(e){}}
function ko(f){return DATA.ko[f]||f}
function G(){return DATA.games[gi]}
function gm(){var id=G().id;return store[id]||(store[id]={})}
function aiOf(f){return (G().ai&&G().ai[f])||[]}
function fm(f){var g=gm();return g[f]||(g[f]={start:aiOf(f).slice(),early:[]})}
function sameSet(a,b){return a.length==b.length&&a.every(function(k){return b.indexOf(k)>=0})}
function hasMarks(id){var g=store[id];if(!g)return false;if(g._ok)return true;
  var gg=null;DATA.games.forEach(function(x){if(x.id==id)gg=x});
  for(var f in g){if(f=="_ok")continue;var a=(gg&&gg.ai&&gg.ai[f])||[];
    if(!sameSet(g[f].start,a)||g[f].early.length)return true}return false}
function diffs(g){var s=store[g.id],out=[];if(!s)return out;
  g.factions.forEach(function(f){var m=s[f];if(!m)return;var a=(g.ai&&g.ai[f])||[];
    var rem=a.filter(function(k){return m.start.indexOf(k)<0}),add=m.start.filter(function(k){return a.indexOf(k)<0});
    if(rem.length||add.length||m.early.length)out.push(ko(f)+" 뺀: "+(rem.join(" ")||"-")+" / 넣은: "+(add.join(" ")||"-")+(m.early.length?" / 초반 땅: "+m.early.join(" "):""))});
  return out}
function changes(){var t=[];DATA.games.forEach(function(g,i){var d=diffs(g);if(d.length)t.push("판 "+(i+1)+" ("+g.id+")\n  "+d.join("\n  "))});
  return t.length?t.join("\n"):"(바뀐 것 없음, AI 그대로)"}
function el(n,a,p){var e=document.createElementNS("http://www.w3.org/2000/svg",n);for(var k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e}
function btn(t,on,fn,col){var b=document.createElement("button");b.textContent=t;if(on)b.className="on";if(col)b.style.borderColor=col;b.onclick=fn;return b}
var S=10,SQ=Math.sqrt(3);
function px(q,r){return[1.5*q*S,SQ*(r+q/2)*S]}
function rotN(q,r,n){var k=((n%6)+6)%6;for(var i=0;i<k;i++){var nq=-r,nr=q+r;q=nq;r=nr}return[q,r]}
var STO=[],DSO=[[0,0],[1,0],[0,1]];
for(var sq=-2;sq<=2;sq++){for(var sr=Math.max(-2,-2-sq);sr<=Math.min(2,2-sq);sr++)STO.push([sq,sr])}
function centroid(offs,oq,or,rot){var sx=0,sy=0;offs.forEach(function(o){var rr=rotN(o[0],o[1],rot),p=px(rr[0]+oq,rr[1]+or);sx+=p[0];sy+=p[1]});return[sx/offs.length,sy/offs.length]}
function hexPts(cx,cy,s){var p=[];for(var i=0;i<6;i++){var a=Math.PI/3*i;p.push((cx+s*Math.cos(a)).toFixed(2)+","+(cy+s*Math.sin(a)).toFixed(2))}return p.join(" ")}
function ui(){
  var d=document.getElementById("games");d.innerHTML="";
  var sel=document.createElement("select");
  DATA.games.forEach(function(g,i){var o=document.createElement("option");o.value=i;
    o.textContent=(hasMarks(g.id)?"✓ ":"")+"판 "+(i+1)+" · "+g.factions.map(ko).join(", ");if(i==gi)o.selected=true;sel.appendChild(o)});
  sel.onchange=function(){gi=+sel.value;fi=0;ui();draw()};d.appendChild(sel);
  d.appendChild(btn("◀",false,function(){if(gi>0){gi--;fi=0;ui();draw()}}));
  d.appendChild(btn("▶",false,function(){if(gi<DATA.games.length-1){gi++;fi=0;ui();draw()}}));
  var f=document.getElementById("facs");f.innerHTML="";
  G().factions.forEach(function(x,i){f.appendChild(btn(ko(x),i==fi,function(){fi=i;ui()},fcol(x,i)))});
  var k=document.getElementById("kinds");k.innerHTML="";
  k.appendChild(btn("스타트",kind=="start",function(){kind="start";ui()}));
  k.appendChild(btn("초반 땅",kind=="early",function(){kind="early";ui()}));
  var n=0;DATA.games.forEach(function(g){if(hasMarks(g.id))n++});
  document.getElementById("cnt").textContent="확인·수정한 판: "+n+" / "+DATA.games.length;
  var ok=document.createElement("button");ok.textContent=(store[G().id]&&store[G().id]._ok?"✓ ":"")+"이 판 확인";
  if(store[G().id]&&store[G().id]._ok)ok.className="on";
  ok.onclick=function(){var s=gm();if(s._ok)delete s._ok;else s._ok=true;save();ui()};k.appendChild(ok);
  document.getElementById("chg").textContent=changes();
}
function toggle(key){
  var m=fm(G().factions[fi]);
  var i=m.start.indexOf(key),j=m.early.indexOf(key);
  if(i>=0)m.start.splice(i,1);
  else if(j>=0)m.early.splice(j,1);
  else if(kind=="start")m.start.push(key);
  else m.early.push(key);
  save();ui();marks();
}
function startPanel(){
  var d=document.getElementById("start");d.innerHTML="";var s=G().start;if(!s)return;
  function row(label,list,tags){
    if(!list.length)return;
    var r=document.createElement("div");r.className="row";
    var l=document.createElement("div");l.className="lab";l.textContent=label;r.appendChild(l);
    list.forEach(function(e,i){
      var t=document.createElement("div");t.className="t";
      if(tags){var b=document.createElement("b");b.textContent=tags[i]||"";t.appendChild(b)}
      if(e[1]){var im=document.createElement("img");im.src=DATA.assets+encodeURIComponent(e[1]);im.alt=e[2];im.loading="lazy";t.appendChild(im)}
      t.appendChild(document.createTextNode(e[2]));r.appendChild(t)});
    d.appendChild(r)}
  var sd=document.createElement("div");sd.className="seats";
  sd.textContent="순서: "+s.seats.map(function(f,i){return (i+1)+". "+ko(f)}).join("  ");d.appendChild(sd);
  if(DATA.board){
    var bi=document.createElement("img");bi.src=DATA.assets+encodeURIComponent(DATA.board);bi.alt="점수판";
    bi.style.width="140px";bi.style.height="auto";bi.style.display="block";bi.style.margin="4px 0";d.appendChild(bi)}
  if(DATA.guide){
    var gd=document.createElement("div");gd.className="seats";gd.style.fontSize="13px";
    var gt=document.createElement("div");gt.textContent="종족별 추천 (오프닝·운영 SH04, 기술 충돌표 판정 · 1R 끝 건물: 의=의회 연=연구소 아=아카데미 교=교역소 광=광산)";gd.appendChild(gt);
    s.seats.forEach(function(f,i){
      var g=DATA.guide[f];if(!g)return;
      var fd=document.createElement("div");
      var nm=document.createElement("b");nm.textContent=ko(f);nm.style.color=fcol(f,i);fd.appendChild(nm);
      var l1=document.createElement("div");l1.textContent="오프닝: "+g[0];fd.appendChild(l1);
      var l2=document.createElement("div");l2.textContent="운영: "+g[1];fd.appendChild(l2);
      if(g[2]){var l3=document.createElement("div");l3.textContent="기술: "+g[2];fd.appendChild(l3);}
      gd.appendChild(fd)});
    d.appendChild(gd)}
  row("라운드 점수 R1–R6",s.rounds,s.rounds.map(function(e,i){return "R"+(i+1)}));
  row("최종 점수",s.final);
  row("부스터",s.boosters);
  var tr=DATA.tracks;
  row("기술 타일",s.std,s.std.map(function(e,i){return i<tr.length?tr[i]:"추가"}));
  row("고급 기술 타일",s.adv,s.adv.map(function(e,i){return i<tr.length?tr[i]:""}));
  function tg(l){return (l||[]).map(function(e){return e[3]||""})}
  row("함선 기술 타일",s.ship_tech||[],tg(s.ship_tech));
  row("함선 연방 토큰",s.ship_fed||[],tg(s.ship_fed));
  row("함선 유물",s.ship_art||[],tg(s.ship_art));
  row("테라포밍 5단계 연방 토큰",s.fed_supply||[],tg(s.fed_supply));
}
function draw(){
  startPanel();
  var svg=document.getElementById("svg");svg.innerHTML="";
  var g=G(),x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  g.hexes.forEach(function(h){var p=px(h[0],h[1]);x0=Math.min(x0,p[0]);x1=Math.max(x1,p[0]);y0=Math.min(y0,p[1]);y1=Math.max(y1,p[1])});
  var m=S*1.2;svg.setAttribute("viewBox",[x0-m,y0-m,x1-x0+2*m,y1-y0+2*m].join(" "));
  el("rect",{x:x0-m,y:y0-m,width:x1-x0+2*m,height:y1-y0+2*m,fill:"#080818"},svg);
  var ag=el("g",{"class":"art"},svg),bg=el("g",{},svg),sg=el("g",{},svg),mg=el("g",{id:"mg","class":"mk"},svg),hg=el("g",{},svg);
  var defs=el("defs",{},ag),A=DATA.assets,fallback=0;
  function href(f){return A+encodeURIComponent(f)}
  // sector art: same placement math as GameBoard (units of S == HEX_SIZE)
  g.sectors.forEach(function(s,si){
    if(!s[4])return;
    var deep=s[0]>=11,offs=deep?DSO:STO,rot=s[3];
    var w=deep?S*3.5:S*8,hh=deep?S*2*SQ:S*5*SQ;
    var photo=deep?1:4;
    var pv=px(s[1],s[2]);
    var cen=centroid(offs,s[1],s[2],photo);
    var ix=deep?cen[0]-w*4/7:cen[0]-w/2,iy=deep?cen[1]-hh*0.5:cen[1]-hh/2;
    var cp=el("clipPath",{id:"c"+si},defs);
    offs.forEach(function(o){var rr=rotN(o[0],o[1],rot),p=px(rr[0]+s[1],rr[1]+s[2]);el("polygon",{points:hexPts(p[0],p[1],S)},cp)});
    var gg=el("g",{"clip-path":"url(#c"+si+")"},ag);
    var im=el("image",{href:href(s[4]),x:ix,y:iy,width:w,height:hh,preserveAspectRatio:"none",transform:"rotate("+((rot-photo)*60)+" "+pv[0]+" "+pv[1]+")"},gg);
    im.setAttribute("style","pointer-events:none");
  });
  // interspace tiles: one hex each, clipped to the hex, 2.1*S square, slice
  g.hexes.forEach(function(h,hi){
    if(!h[3])return;var p=px(h[0],h[1]),sz=S*2.1;
    var cp=el("clipPath",{id:"i"+hi},defs);el("polygon",{points:hexPts(p[0],p[1],S)},cp);
    var gg=el("g",{"clip-path":"url(#i"+hi+")"},ag);
    el("image",{href:href(h[3]),x:p[0]-sz/2,y:p[1]-sz/2,width:sz,height:sz,preserveAspectRatio:"xMidYMid slice"},gg);
  });
  g.hexes.forEach(function(h){
    var p=px(h[0],h[1]);
    el("polygon",{points:hexPts(p[0],p[1],S),"class":"hx"},bg);
    if(h[2]&&!h[4]){fallback++;var c=PC[h[2]]||"#999";
      if(h[2]=="Asteroid"){for(var i=0;i<5;i++){var a=i*1.256;el("circle",{cx:p[0]+3.4*Math.cos(a),cy:p[1]+3.4*Math.sin(a),r:1.9,fill:"#9aa5b1"},bg)}}
      else{var e=el("circle",{cx:p[0],cy:p[1],r:S*0.5,fill:c,stroke:"#000","stroke-width":.6},bg);
        if(h[2]=="LostPlanet"){e.setAttribute("stroke","#fff");e.setAttribute("stroke-width",1.6)}}}
  });
  document.getElementById("legend").style.display=fallback?"block":"none";
  g.hexes.forEach(function(h){
    var p=px(h[0],h[1]),key=h[0]+","+h[1];
    var pl=el("polygon",{points:hexPts(p[0],p[1],S),"class":"hit"},hg);
    pl.addEventListener("click",function(){toggle(key)});
  });
  marks();
}
function marks(){
  var mg=document.getElementById("mg");mg.innerHTML="";
  var g=G(),gmk=store[g.id]||{};
  g.factions.forEach(function(f,i){
    var ai=aiOf(f),m=gmk[f]||{start:ai.slice(),early:[]};var col=fcol(f,i),lab=ko(f).replace(/\s/g,"").slice(0,2);
    ai.forEach(function(k){if(m.start.indexOf(k)<0){var xy=k.split(","),p=px(+xy[0],+xy[1]);
      el("circle",{cx:p[0],cy:p[1],r:S*(0.78-i*0.06),fill:"none",stroke:col,"stroke-width":.8,"stroke-dasharray":"1.5 1.5","stroke-opacity":.55},mg)}});
    function put(key,txt,big){var xy=key.split(",");var p=px(+xy[0],+xy[1]);
      var off=(i-1.5)*1.6;
      if(big&&ai.indexOf(key)<0)el("circle",{cx:p[0],cy:p[1],r:S*(0.78-i*0.06)+1.6,fill:"none",stroke:"#fff","stroke-width":1.4},mg);
      el("circle",{cx:p[0],cy:p[1],r:S*(0.78-i*0.06),fill:"none",stroke:"#000","stroke-width":(big?2.2:1.6)+1.2},mg);
      el("circle",{cx:p[0],cy:p[1],r:S*(0.78-i*0.06),fill:"none",stroke:col,"stroke-width":big?2.2:1.6},mg);
      var t=el("text",{x:p[0]+off,y:p[1]+S*(0.35),"font-size":4,"text-anchor":"middle",fill:col,stroke:"#000","stroke-width":.5,"paint-order":"stroke","font-weight":"bold"},mg);
      t.textContent=txt}
    m.start.forEach(function(k,j){put(k,lab+"S"+(j+1),true)});
    m.early.forEach(function(k,j){put(k,lab+(j+1),false)});
  });
}
function result(){
  var o={};o[DATA.exp]={};
  DATA.games.forEach(function(g){var s=store[g.id];if(!s)return;var r={};
    for(var f in s){if(f=="_ok")continue;if(s[f].start.length||s[f].early.length)r[f]={start:s[f].start,early:s[f].early}}
    if(Object.keys(r).length||s._ok)o[DATA.exp][g.id]=r});
  return JSON.stringify(o);
}
document.getElementById("copy").onclick=function(){
  var t=result(),ta=document.getElementById("ta");
  function fb(){ta.style.display="block";ta.value=t;ta.focus();ta.select()}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(function(){alert("복사됨")},fb)}else fb();
};
document.getElementById("clear").onclick=function(){
  if(confirm("이 판의 표시를 모두 지울까요?")){delete store[G().id];save();ui();marks()}
};
var lg=document.getElementById("legend");
Object.keys(PK).forEach(function(k){var s=document.createElement("span");var i=document.createElement("i");i.style.background=PC[k];if(k=="Asteroid")i.style.background="#9aa5b1";s.appendChild(i);s.appendChild(document.createTextNode(PK[k]));lg.appendChild(s)});
ui();draw();
</script></div></body></html>
"""

if __name__ == "__main__":
    main()
