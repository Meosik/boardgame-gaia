"""Per-faction starting-booster preferences from the faction booster claims (faction-claims-status.md, category 부스터),
added to booster_tier_value in teacher_patches (ships_menu1_all_tier, user 2026-10-25 night, HANDOFF E117)."""

# Delta scale: +1.5 top pick / "최우선" / "무조건"; +1.0 preferred / "매우 좋다" / "좋다"; +0.5 weakly preferred / "무난";
# -0.5 "선호하지 않는다" / "비권장"; -1.0 avoid / "별로"; -1.5 strongly avoid ("최악", "택하지 마라").
# Booster ids: 1 lab-VP 2 ore+2 tokens 3 mine-VP 4 big-building 5 instant gaia 6 gaiaformer-VP 7 trading-VP
# 8 range+3 9 QIC+2 credits 10 planet-type-VP 11 4 credits+gaia-VP 12 terraform 1 step 13 ore+knowledge 14 deep-space.
#
# Conflicts: Lantids 4 PG06-S15 (R1 trap, -1.5 kept) vs PG06-S19 (good from 2R); Geodens 3 PG08-T07 (R1 avoid, kept)
# vs PG08-T09 (good all game except R1); BalTaks 12 PG14-S35 (+0.5) vs B11-S04 (terrain dependent).
# Not mapped: PG10-S23 Nevlas "큐빅 부스터를 고르는 실수" (which booster is unclear); PG22-S31 Ivits 11 "조금 낫다" (no sign);
# PG24-S26 Geodens 10 (LF speculation, low confidence); PG18-T14 Terrans 8 ("좋지만 평균보다 낮음", 0).
#
# Conditional (not encoded):
# Conditional (not encoded): PG13-S40 Bescods: 3 (mine-VP) good only for an aggressive early expansion.
# Conditional (not encoded): PG17-S22 Firaks: 9 (QIC+2 credits) when opening council+lab (convert QIC to ore).
# Conditional (not encoded): PG17-S41 Firaks: 4 (big building) only in R1 council+lab opening with a sure 2-ore power action.
# Conditional (not encoded): PG17-S42 Firaks: 2 (ore+2 tokens) when power is piled in bowls 2/3 at round end.
# Conditional (not encoded): PG17-S43 Firaks: 12 and 8 very good for lab+trading+2-mine opening (12 useless with council opening).
# Conditional (not encoded): PG19-S40 HadschHallas: 9 and 12 good for a mine-expansion opening (no synergy with academy opening).
# Conditional (not encoded): PG19-S41 HadschHallas: 2 good after council (charge 8) but later prefers VP boosters; 1 about 6 VP if 2nd lab opens in R2-3.
# Conditional (not encoded): H05 HadschHallas: 11 (credits) low value when credits are already plentiful.
# Conditional (not encoded): PG04-S39 Gleens: when range+3 is gone, aim for 3 (mine-VP, 7-8 VP in R1) or 11 (credits+gaia-VP).
# Conditional (not encoded): PG04-S40 Gleens: when range+3 is gone, consider 12 (terraform) to hop over distance-2 gaps.
# Conditional (not encoded): PG04-S41 Gleens: 7 (trading-VP) timed to R2 trading build, 4 (big building) mid/late game, never untimed (later rounds).
# Conditional (not encoded): PG04-S42 Gleens: 1 is fine only if labs are built in the last round or R4-6 (encoded -1.0 as base).
# Conditional (not encoded): PG14-S35 BalTaks: 2 (ore+2 tokens) only when placing 3 gaiaformers at once (7 to 9 tokens).
# Conditional (not encoded): B11-S04 BalTaks: 12 (terraform) good depending on terrain.
# Conditional (not encoded): PG20-S31 Ambas: 1 (lab-VP) when a lab-VP advanced tile sits above navigation and the booster is out.
# Conditional (not encoded): PG20-S34 Ambas: 8 (range+3) always taken if a 5-hop jump grabs a third cluster in R1 (encoded -0.5 as base).
# Conditional (not encoded): PG23-S33 Itars: 3 (mine-VP) especially good in a council opening (many mines).
# Conditional (not encoded): PG09-S23 Nevlas: when Nevlas is last to pick, others should take 4 (big building) first to deny it.
# Conditional (not encoded): PG10-S25 Nevlas: 1 (lab-VP) is the best VP booster, take in R4 and R6 (later rounds).
# Conditional (not encoded): PG10-S26 Nevlas: if 4 is gone, 9 or 13 in R1; 8 (range+3) good but used in R2-3.
# Conditional (not encoded): PG10-S27 Nevlas: 2 (ore+2 tokens) when next-round charge tokens will be short (mid game after federation).
# Conditional (not encoded): PG15-T18 Xenos: with 4th pick take 12/8 instead of 9; 4/3/1/11 good depending on map and opponents; 12 fits a navigation opening.
# Conditional (not encoded): X06 Xenos: 9 strong when it enables a tech action and expansion together; 8 and 12 swing games by securing key planets.
# Conditional (not encoded): PG08-T05 Geodens: 12 best when opening council in R1, otherwise it should be picked last.
# Conditional (not encoded): PG08-T06 Geodens: when not opening council in R1, 8 very good and 9 is hard to get wrong.
# Conditional (not encoded): PG08-T08 Geodens: 13 good when opening council in R1 and colonizing exactly one new planet type.
# Conditional (not encoded): PG08-T09 Geodens: 11 only from R2 on when credits are desperate.
FACTION_BOOSTER_PREFS = {
    # B13-S11 PG13-S39 PG13-S40 PG13-S42
    'Bescods': {13: 1.0, 8: 1.0, 1: 1.0, 4: -1.0, 9: 1.0, 12: 1.0, 2: -0.5},
    # PG17-S42 PG17-S44
    'Firaks': {13: 0.5, 7: 1.0, 11: -1.5, 3: -1.0, 1: -1.5},
    # PG06-S15 PG06-S16 PG06-S17 PG06-S18 PG06-S19
    'Lantids': {4: -1.5, 3: 1.5, 13: 1.0, 9: 1.0, 12: -1.5, 8: -1.5, 11: -1.0, 2: -1.0, 1: -0.5},
    # PG22-S31 PG22-S32 PG22-S33 PG22-S34
    'Ivits': {3: -1.0, 7: -1.0, 13: 1.0, 1: 1.0, 4: 1.5, 8: 1.0, 12: 1.0, 9: 1.0},
    # H05 PG19-S39 PG19-S40 PG19-S41
    'HadschHallas': {4: 1.0, 13: 1.0, 3: -0.5, 11: -0.5},
    # B11-S04 PG14-S34 PG14-S35
    'BalTaks': {8: 1.5, 9: 1.5, 11: 1.0, 13: 1.0, 12: 0.5, 4: 0.5},
    # PG04-S37 PG04-S38 PG04-S42
    'Gleens': {9: -1.5, 8: 1.5, 1: -1.0},
    # PG18-T14 PG18-T15
    'Terrans': {11: 1.5, 13: 1.0, 12: 1.0, 1: 0.5, 2: -1.5, 4: -1.0},
    # PG21-T25
    'Taklons': {11: -1.0, 7: -1.0, 3: -1.0, 1: 1.0, 4: 1.5, 8: 0.5},
    # PG20-S29 PG20-S30 PG20-S32 PG20-S34
    'Ambas': {12: 1.0, 11: 0.5, 9: 1.0, 4: 1.0, 8: -0.5},
    # PG23-S32 PG23-S33 PG23-S34 PG23-S35
    'Itars': {2: 1.0, 4: 1.0, 7: -1.0, 1: -1.0, 11: 1.0, 13: 1.0, 9: 0.5, 8: 1.0, 12: -0.5},
    # PG10-S23 PG10-S26
    'Nevlas': {4: 1.5, 3: -0.5, 7: -1.0},
    # PG15-T18
    'Xenos': {9: 1.5},
    # B14-S11 PG08-T04 PG08-T07
    'Geodens': {4: 1.5, 9: 0.5, 8: 0.5, 12: -0.5, 2: -1.0, 3: -1.0, 7: -1.0},
}
