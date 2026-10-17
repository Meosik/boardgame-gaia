# IRIS — 가이아 프로젝트 공략 [기본 가이드라인] (IR01), read in full

Source: iris, "IRIS의 가이아 프로젝트 공략 [기본 가이드라인]", Naver blog, 2022-04-12, saved page
(`docs/references/discord/1560892963318538381-IRIS`, text extracted to `iris-basic-guideline.txt` with
`tools/mhtml_text.py`; both git-excluded). Received from the user on 2026-10-17 as material, not an instruction.
Author: BGS Elo #1 at one time, BGA season #2; 4-player base game; the article says it is deliberately
common-strategy, points to uiqoo (어잌후) for faction detail, and is "strongly the author's own style".
Only paraphrased claims are kept here. 1 VP = 1.5 charges is not used by this author; their unit is
1 ore = 3 credits = 1 knowledge.

Scope rule as for the other articles: facts are computed exactly; within-horizon outcomes are left to
search; judgments may only order proposals.

| # | Claim (IR01) | Kind | Relation to what we have |
|---|---|---|---|
| 1 | Resource parity 1 ore = 3 credits = 1 knowledge; credits/knowledge slightly dearer because income is scarce | value (author) | LF01 uses charge prices (ore 3 charges?) — not swapped in; author's own scale |
| 2 | Mines are the only basic income growth; aim for all 8 mines by round 4 ("spreading mines fast is always strong") | judgment | agrees with B01/B19 (Taklons 연5광), BGG RL+nM n≥5 rows |
| 3 | Early mine growth = 1-terraform power action + QIC on Gaia planets at range 2; 1 QIC ≈ 1 terraform ≈ 1 ore, so a new mine costs about 2 ore 2 credits | fact-ish | matches our ore accounting (ore_sources.py); power action 3 / terraform actions already candidates |
| 4 | A trading station alone adds no income (−1 ore +3 credits); it is only the step to a lab. Credits come from the 4-credit tech tile, the 7-credit power action in R1–2, then federation 6 credits and the 3-QIC action from R4 | judgment → order | agrees with B01/B02 (3rd mine, TS are loss on their own) and ts_chain (TS only when it leads to RL/PI) |
| 5 | Lab = "5 ore 8 credits for a tech tile + 1 track step" (TS folded in); built in R1 by almost every faction except PI-first ones; default track Navigation, Economy/Science only with synergy or a good advanced tile | judgment → order | matches SH03 "1R 연구소는 무조건"; Navigation default conflicts with B14 Geodens (eco/sci) — IRIS lists Geodens as PI-first anyway |
| 6 | Academy 6 ore 6 credits ≈ lab cost but strictly better (knowledge academy +1 income); build in R2–3, inside the first federation, ideally on a "big building 5 VP" round | judgment | B02 agrees (knowledge AC better than 2 labs) |
| 7 | **R1 academy needs extra ore: at least 11 ore 14 credits, with one mine 12 ore 16 credits. Most factions start R1 with 8 ore 15 credits (ore booster taken), so 3–4 ore more: usually 1–2 from power free actions, the other 2 from terraforming track level 1 or the [1 ore 1 QIC] tech tile; if the 2-ore power action succeeds, the 4-power tech tile alone can be enough. An AC-first round leaves no resources for mines, so it pairs with economy/science builds, not navigation** | fact (costs) + judgment (sources) | identical arithmetic to B11/B14 and to our HANDOFF note (11/12 ore, 3–4 from conversions). Source list for the gap is the useful new part |
| 8 | **AC-first in R1 only for Itars, BalTaks, Taklons; for everyone else the lab (navigation) build is better because AC-first loses the R1–2 planet race** | judgment | **conflicts with the uiqoo orders we apply**: Geodens B14 1AC+2M first, Terrans 1AC+1M first (B04/B19). IRIS puts Geodens as PI-first (terraforming or navigation), Terrans as navigation-lab |
| 9 | Itars: AC income is 3 knowledge; 8-knowledge build reaches Nav 2 in R2; PI in R3 — AC-first is right. BalTaks: no navigation use, AC-first + 4-QIC action. Taklons: AC-first fine if power comes, but lab(nav) R1 → AC R2 is often better; AC-first when the 4-power tile sits on eco/sci or a good advanced tile is there | judgment | Taklons: agrees with B19 (연5광 over 아광광) and with our UIQOO Taklons order being 1AC+2M first only via B10 (2019) |
| 10 | 3 federations = 21 power is the default goal; rule of thumb: with 2 big buildings, 3 federations are possible with 5 buildings left unbuilt; with 1 big building, 4 left. A 4th federation costs ≈ one more big building (12 ore 16 credits) for 12 VP — only with spare resources, no good advanced tile, and a building mission to win (double building mission especially) | judgment | agrees with C001 (≥3 federations); the "buildings left" rule is a computable fact we do not use |
| 11 | 4 federations are natural for Hive (+6 power), Ambas (PI R3 with big-building-4 tile → 5 fed, else PI R4 → 4), Mad Androids (only with 5–6 own planets), Xenos possible but not recommended — Xenos are often stronger skipping the PI and taking 3 federations, lab instead of PI | judgment | Xenos: matches our X-series claims (PI 먼저 짓지 말고 연구소) |
| 12 | The first federation decides advanced-tile priority; plan its shape and round from R1; usually R3, at latest R4 (Hive/Lantids R1–2). Default shape [AC/PI + 4 mines]; variant [AC/PI + 2 mines + TS/RL]; PI+AC factions (Itars) use [PI + AC + 1 mine] in R3, needs two adjacent hexes next to an opponent for the 3-credit TS discount | judgment → plan shape | our federation goal code has no target shape; "연방 안 함" plan comparison is on the agenda |
| 13 | Advanced tiles worth ≥20 VP are priority: pass 3 VP per lab (27 with 3 labs, S-tier; delay the academy to keep 3 labs), pass 3 VP per federation (18–21, 30 for 4-fed factions, Hive), 3 VP per mine built (18–21 after a nav opening, ~30 on eco/sci), 2 VP per research step (12–14 normally, 20–30 for Itars/Mad Androids on the knowledge track) | judgment/value | LF02 has advanced-tile tiers already; numbers here are the author's |
| 14 | **Navigation opening (recommended for Ambas, Taklons, HadschHallas, Terrans, Xenos, Gleens; optional Firaks, Mad Androids; not for Itars, BalTaks, Hive, Nevlas, Lantids, Geodens)**: track order Nav 2 → Terraforming 5 → AI 4–5 → Nav 4; economy track not recommended unless knowledge faction | judgment → order | per-faction split; see 8 |
| 15 | R1: lab + 4-credit tile (Taklons/Terrans 4-power tile; HadschHallas anything but 4-credit) + Nav 2; grab the 1-terraform power action; QIC on Gaia/home planets at range 2; 2-terraform action if it links home planets at range 2 | judgment → order | our R1 rules: first tech 4-charge for Terrans/Taklons (B04/B10) agree |
| 16 | R2: academy if 6 ore (delay if R3 is "big building 5 VP"); 2-knowledge power action → 4 knowledge → terraforming 1 → 6 ore → academy is a line; academy tile on the terraforming track; else keep 1-terraform action + QIC mines | judgment → order | — |
| 17 | R3: academy if not yet; terraforming 3; spread the remaining mines; first federation [AC + 4 mines] if possible | judgment → order | — |
| 18 | R4: terraforming 5 via the knowledge-per-planet tile; if taken, stop at 3 and go AI for 2–3 QIC actions (AI before Nav 3); federation if not yet; round/mission VP | judgment → order | agrees with B14 (AI from R4) |
| 19 | R5–6: AI + 2–3 QIC actions, 2nd and 3rd federations, round/mission VP | judgment → order | — |

What is new for the current work (2026-10-17, Geodens academy stall):

- Row 7 is a third independent statement of the same arithmetic (11 ore without a new mine, 12 with one; the
  gap of 3–4 ore is filled by power free actions, terraforming level 1 (Geodens have it), the 1-ore-1-QIC tile
  or the 2-ore power action). It supports the proposed `select_action` change (upgrade before mines; funding
  actions must cover the academy) and names the funding sources in order.
- Row 8 is a direct disagreement with the uiqoo opening orders the user chose to apply ("자료대로"): IRIS would
  not open AC-first with Geodens or Terrans at all. Not applied; recorded as a conflict for the user to decide
  (the author also defers to uiqoo for faction detail).
- Rows 10 and 12 contain computable facts (buildings-left rule for 21 power, federation target shapes) that
  could become proposal orders for the "no federation / first federation shape" agenda item.
