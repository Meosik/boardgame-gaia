#!/usr/bin/env python3
"""
Gaia Project BGA 스프라이트 크롭 스크립트
CSS 좌표 기반으로 각 컴포넌트를 개별 파일로 저장
"""

from PIL import Image
import os

SRC_DIR = os.path.expanduser("~/projects/gaia/assets/images")
OUT_DIR = os.path.expanduser("~/projects/gaia/assets/images")

os.makedirs(OUT_DIR, exist_ok=True)

# ── 행성 크롭 (planets.png, 132x132px 단위) ──
PLANET_NAMES = {
    0: "blue",       # Terrans
    1: "red",        # Bal-Taks / Hadsch Hallas
    2: "volcanic",   # Firaks
    3: "yellow",     # Geodens
    4: "brown",      # Ambas
    5: "gray",       # Bescods
    6: "white",      # Nevlas
    7: "green",      # Xenos
    8: "purple",     # Taklons
    9: "transdim",   # 트랜스딤 행성
}

planets = Image.open(f"{SRC_DIR}/planets.png")
pw = 132
os.makedirs(f"{OUT_DIR}/planets", exist_ok=True)
for i, name in PLANET_NAMES.items():
    x = i * pw
    crop = planets.crop((x, 0, x + pw, 132))
    crop.save(f"{OUT_DIR}/planets/{name}.png")
    print(f"  planets/{name}.png")

# ── 건물 크롭 (structures.png) ──
# 종족별 y 오프셋 (race1,2=0, race3,4=-200, ...)
# structure type별 x 오프셋 및 width
# structure1: 연구마커 x=-850 w=62
# structure2: 광산 x=0(750 offset) w=109  (실제: x=750, w=109)
# structure3: 교역소 → icons.png 별도
# structure4: 행성기지 x=750 w=69
# structure5: 연구소 x=450 w=102
# structure6: 아카데미 x=600 w=108
# structure7,8: 파이어웍 x=250 w=186

RACE_NAMES = {
    1: "terrans", 2: "terrans_alt",
    3: "hadsch", 4: "hadsch_alt",
    5: "ivits", 6: "ivits_alt",
    7: "geodens", 8: "geodens_alt",
    9: "baltaks", 10: "baltaks_alt",
    11: "taklons", 12: "taklons_alt",
    13: "ambas", 14: "ambas_alt",
}

STRUCTURE_INFO = {
    "mine":        {"x": 0,   "w": 200, "h": 200},  # 광산 (왼쪽 200px)
    "tradingpost": {"x": 200, "w": 200, "h": 200},  # 교역소
    "researchlab": {"x": 400, "w": 200, "h": 200},  # 연구소
    "academy":     {"x": 600, "w": 200, "h": 200},  # 아카데미/행성기지
}

structures = Image.open(f"{SRC_DIR}/structures.png")
os.makedirs(f"{OUT_DIR}/structures", exist_ok=True)

for race_num, race_name in RACE_NAMES.items():
    y_offset = ((race_num - 1) // 2) * 200
    for struct_name, info in STRUCTURE_INFO.items():
        x = info["x"]
        w = info["w"]
        h = info["h"]
        crop = structures.crop((x, y_offset, x + w, y_offset + h))
        fname = f"{race_name}_{struct_name}.png"
        crop.save(f"{OUT_DIR}/structures/{fname}")
        print(f"  structures/{fname}")

# ── 연맹 토큰 크롭 (federationTokens.png, 96x119px 단위) ──
fed = Image.open(f"{SRC_DIR}/federationTokens.png")
os.makedirs(f"{OUT_DIR}/federation", exist_ok=True)
fw, fh = 96, 119
for i in range(1, 8):
    x = i * fw
    crop = fed.crop((x, 0, x + fw, fh))
    crop.save(f"{OUT_DIR}/federation/token{i}.png")
    print(f"  federation/token{i}.png")

# ── 기술 타일 크롭 (techs.png, 148px 단위) ──
techs = Image.open(f"{SRC_DIR}/techs.png")
th = techs.size[1]
os.makedirs(f"{OUT_DIR}/techs", exist_ok=True)
tw = 148
for i in range(1, 25):
    x = i * tw
    crop = techs.crop((x, 0, x + tw, th))
    crop.save(f"{OUT_DIR}/techs/tech{i}.png")
    print(f"  techs/tech{i}.png")

print("\n✅ 크롭 완료!")
print(f"저장 위치: {OUT_DIR}")
