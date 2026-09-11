"""Korean descriptive names for id-addressed tile assets.

Files are named `<prefix>_<NN>_<설명>[_<단계>].<ext>`. Runtime lookups only read the
`<prefix>_<NN>` part (see `src/assets/assetIndex.ts`), so a description can be corrected here and
in the file name without touching any code path. Every name below was checked against the image
itself, not only against engine data.
"""

from __future__ import annotations

import unicodedata

ROUND_BOOSTERS = {
    1: "지식1_패스연구소당3점",
    2: "광석1_파워토큰2",
    3: "광석1_패스광산당1점",
    4: "파워충전4_패스의회아카데미당4점",
    5: "파워충전2_즉시가이아행동",
    6: "광석1_패스가이아포머당3점",
    7: "광석1_패스교역소당2점",
    8: "파워충전2_사거리3행동",
    9: "크레딧2_정보큐브1",
    10: "광석1_패스행성종류당1점",
    11: "크레딧4_패스가이아행성당1점",
    12: "크레딧2_테라포밍1단계행동",
    13: "광석1_지식1",
    14: "크레딧3_패스심우주구역당2점",
}

# Named after the printed image. Ids 10 and 11 currently disagree with
# `RoundTile::from_id` in gaia-engine, which maps 10 to a new planet type and 11 to a new sector.
ROUND_SCORING_TILES = {
    0: "뒷면",
    1: "광산건설_2점",
    2: "테라포밍단계_2점",
    3: "가이아광산_4점",
    4: "교역소_3점",
    5: "연방형성_5점",
    6: "의회아카데미_5점",
    7: "가이아광산_3점",
    8: "교역소_4점",
    9: "연구단계_2점",
    10: "새구역광산_3점",
    11: "새행성종류광산_3점",
    12: "연구소_4점",
}

FINAL_SCORING_TILES = {
    1: "최다가이아행성",
    2: "최다심우주구역",
    3: "최다연방소속건물",
    4: "최다행성종류",
    5: "최다건물",
    6: "최다소행성",
    8: "최다구역",
    9: "의회아카데미최장거리",
    10: "최다위성",
}

FEDERATION_TOKENS = {
    1: "12점",
    2: "8점_정보큐브1",
    3: "8점_파워토큰2",
    4: "7점_광석2",
    5: "7점_크레딧6",
    6: "6점_지식2",
    8: "함선_8점_크레딧8",
    9: "함선_12점",
    10: "함선_4점_지식4",
    11: "함선_4점_광석2_정보큐브1",
    12: "함선_기술타일선택",
    13: "함선_7점_3구역파워토큰2",
    14: "함선_테라포밍3단계광산",
    15: "함선_무제한사거리광산",
    16: "글린전용_광석1_지식1_크레딧2",
}

ARTIFACTS = {
    1: "심우주구역당3점",
    2: "수입_3구역파워토큰2",
    3: "수입_광석1_지식1",
    4: "가이아프로젝트레벨당3점",
    5: "과학레벨당3점",
    6: "크레딧3_광석3",
    7: "지식3_정보큐브1",
    8: "7점_원시행성광산",
    9: "크레딧5_광석2",
    10: "보유연방토큰효과복사",
    11: "3점_행성종류당1점",
    12: "7점_소행성광산",
    13: "연구3레벨이상분야당3점",
}

# Engine tile ids (`TinkeroidsUseTile`), not the original scan order.
TINKERING_TILES = {
    1: "1-3라운드_테라포밍1단계광산",
    2: "1-3라운드_정보큐브1",
    3: "1-3라운드_파워충전4",
    4: "4-6라운드_정보큐브2",
    5: "4-6라운드_테라포밍3단계광산",
    6: "4-6라운드_지식3",
}

INTERSPACE_TILES = {
    1: "빈칸",
    2: "이클립스",
    3: "TF마스",
    4: "리벨리온",
    5: "트와일라잇",
    6: "소행성",
    7: "원시행성",
}

STANDARD_TECH_TILES = {
    2: "수입광석1_파워충전1",
    3: "수입크레딧4",
    4: "즉시광석1_정보큐브1",
    5: "수입지식1_크레딧1",
    6: "의회아카데미파워가치증가",
    7: "즉시7점",
    8: "가이아광산건설시3점",
    9: "즉시행성종류당지식1",
    10: "행동파워충전4",
    11: "함선_테라포밍2단계광산",
    12: "함선_기본사거리1증가",
    13: "함선_즉시광석1_지식3",
}

ADVANCED_TECH_TILES = {
    1: "즉시교역소당4점",
    2: "즉시연방토큰당5점",
    3: "교역소업그레이드시3점",
    4: "광산건설시3점",
    5: "즉시구역당광석1",
    6: "즉시구역당2점",
    7: "패스연구소당3점",
    8: "연구진행시2점",
    9: "즉시가이아행성당2점",
    10: "즉시광산당2점",
    11: "패스연방토큰당3점",
    12: "즉시심우주구역당4점",
    13: "즉시대형건물당6점",
    14: "패스소행성당2점",
    15: "패스심우주구역당2점",
    16: "정보큐브행동시4점",
    17: "테라포밍단계당2점",
    19: "패스행성종류당1점",
    20: "행동지식3",
    21: "행동광석3",
    22: "행동정보큐브1_크레딧5",
}


def asset_filename(
    prefix: str,
    asset_id: int,
    names: dict[int, str],
    extension: str,
    stage: str = "",
) -> str:
    """Return e.g. `fed_06_6점_지식2_회색면.webp`; NFC keeps names identical across tools."""

    stage_part = f"_{stage}" if stage else ""
    name = f"{prefix}_{asset_id:02d}_{names[asset_id]}{stage_part}.{extension}"
    return unicodedata.normalize("NFC", name)
