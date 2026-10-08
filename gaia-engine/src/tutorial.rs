//! Fixed teaching script; all progress after setup goes through the ordinary rules engine.
//! Base rules pp.11–18 and Lost Fleet pp.9–15 govern the actions; only the initial
//! resources, prepared structures, research level and gifted token are teaching allowances.
use crate::{game_state::*, rules::actions::*, MapEngine, Randomizer, RuleEngine, RuleError};
use serde::{Deserialize, Serialize};

pub const SCRIPT_ID: &str = "round1-v1";
pub const SEED: &str = "tutorial-round1-v1";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialState {
    pub script_id: String,
    pub step: usize,
    pub steps: Vec<TutorialStep>,
    pub introduction: Vec<String>,
    pub opponents: Vec<TutorialMove>,
    pub final_scores: Option<[crate::FinalScoreBreakdown; 4]>,
    pub final_tiles: Vec<TutorialFinalTile>,
    #[serde(default)]
    pub feedback: TutorialFeedback,
    #[serde(default)]
    pub income: Vec<TutorialIncome>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialFinalTile {
    pub tile_id: u8,
    pub scores: [(PlayerId, i32); 4],
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialMove {
    pub player: PlayerId,
    pub action: GameAction,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialStep {
    pub title: String,
    pub instruction: String,
    pub reason: String,
    pub target: String,
    pub action: GameAction,
    #[serde(default)]
    pub timings: Vec<String>,
}

/// Amounts are ore, credits, knowledge, QIC, printed charge, new tokens, VP.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialIncomeRow {
    pub source: String,
    pub amounts: [i32; 7],
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialIncome {
    pub round: u8,
    pub rows: Vec<TutorialIncomeRow>,
}
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TutorialFeedback {
    pub scores: Vec<TutorialScore>,
    pub pass: Vec<String>,
}
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TutorialScore {
    pub amount: i32,
    pub source: String,
    pub reason: Option<VpReason>,
}

fn effect_timings(action: &GameAction) -> Vec<String> {
    use GameAction::*;
    let labels: &[&str] = match action {
        ChooseIncomeOrder { .. } => &["수입 때마다"],
        Pass { .. } => &["패스할 때", "수입 때마다"],
        PowerAction { .. }
        | TechTileSpecialAction { .. }
        | AcademyQicAction
        | RoundBoosterRangeExploreSpaceship { .. }
        | SpaceshipCreditTerraform { .. } => &["라운드당 1회 행동"],
        TwilightReplayFederationToken { .. } => &["라운드당 1회 행동", "즉시 1회"],
        Upgrade {
            tech_tile_choice:
                Some(TechTileChoice::Standard {
                    tile: TechTile(10), ..
                }),
            ..
        } => &["수입 때마다", "라운드당 1회 행동"],
        Upgrade {
            tech_tile_choice: Some(TechTileChoice::Advanced { .. }),
            ..
        } => &["즉시 1회", "라운드당 1회 행동", "수입 때마다"],
        Upgrade {
            tech_tile_choice: Some(TechTileChoice::LostFleetAdvanced { .. }),
            ..
        } => &["패스할 때", "수입 때마다"],
        Upgrade {
            to: StructureType::Academy(_),
            ..
        } => &["즉시 1회", "라운드당 1회 행동"],
        Upgrade {
            tech_tile_choice: Some(_),
            ..
        }
        | ResearchAdvance { .. }
        | ExamineArtifact { .. }
        | FormFederation { .. } => &["즉시 1회"],
        Build { .. } | Upgrade { .. } => &["수입 때마다"],
        _ => &["즉시 1회"],
    };
    let mut timings: Vec<String> = labels.iter().map(|s| (*s).into()).collect();
    // This scenario fixes round one to the mine scoring tile.
    if matches!(action, Build { .. } | SpaceshipCreditTerraform { .. }) {
        timings.push("~할 때마다".into());
    }
    timings
}

/// Read-only Terran income projection for this fixed script, in engine grant order.
/// Base mine/lab production belongs to the faction board, exposed building slots
/// to buildings. This deliberately does not execute actions on a modified state.
pub fn income_breakdown(state: &GameState, round: u8) -> TutorialIncome {
    let p = &state.players[0];
    let mut rows = Vec::new();
    let mut remaining = [
        15 - i32::from(p.resources.ore),
        30 - i32::from(p.resources.credits),
        15 - i32::from(p.resources.knowledge),
    ];
    let mut add = |source: String, mut amounts: [i32; 7]| {
        for i in 0..3 {
            amounts[i] = amounts[i].min(remaining[i].max(0));
            remaining[i] -= amounts[i];
        }
        rows.push(TutorialIncomeRow { source, amounts });
    };
    for track in [ResearchTrack::Economy, ResearchTrack::Science] {
        let level = p.research_tracks.get(track);
        if level > 0 && level < 5 {
            if let Some(e) = crate::data::get_level_effect(track.as_str(), level) {
                let mut amounts = [
                    i32::from(e.ore),
                    i32::from(e.credits),
                    i32::from(e.knowledge),
                    i32::from(e.qic),
                    i32::from(e.power_charge),
                    0,
                    0,
                ];
                if track == ResearchTrack::Economy && matches!(level, 3 | 4) {
                    if state.research_board.economy_research_tile_side
                        == EconomyResearchTileSide::Power
                    {
                        amounts[1] = 2;
                        amounts[4] = if level == 3 { 3 } else { 2 };
                    } else {
                        amounts[4] = 0;
                        amounts[6] = 1;
                    }
                }
                add(format!("연구 · {track:?} {level}단계"), amounts);
            }
        }
    }
    if let Some(Booster(id)) = p.booster {
        let amounts = match id {
            1 => [0, 0, 1, 0, 0, 0, 0],
            8 => [0, 0, 0, 0, 2, 0, 0],
            _ => [0; 7],
        };
        add(format!("부스터 {id}"), amounts);
    }
    add("종족 보드 · 기본 광석·지식".into(), [1, 0, 1, 0, 0, 0, 0]);
    let count = |kind| p.structures.iter().filter(|s| s.kind == kind).count();
    let mines: i32 = [1, 1, 0, 1, 1, 1, 1, 1]
        .iter()
        .take(count(StructureType::Mine))
        .sum();
    let credits: i32 = [3, 4, 4, 5]
        .iter()
        .take(count(StructureType::TradingStation))
        .sum();
    add("건물 · 광산".into(), [mines, 0, 0, 0, 0, 0, 0]);
    add("건물 · 교역소".into(), [0, credits, 0, 0, 0, 0, 0]);
    add(
        "건물 · 연구소".into(),
        [0, 0, count(StructureType::ResearchLab) as i32, 0, 0, 0, 0],
    );
    if count(StructureType::PlanetaryInstitute) > 0 {
        add("건물 · 의회".into(), [0, 0, 0, 0, 4, 1, 0]);
    }
    TutorialIncome { round, rows }
}

fn score_feedback(
    before: &GameState,
    after: &GameState,
    action: &GameAction,
    events: &[GameEvent],
) -> Vec<TutorialScore> {
    let id = before.players[0].player_id;
    let mut scores: Vec<_> = events
        .iter()
        .filter_map(|event| {
            if let GameEvent::VpAwarded {
                player,
                amount,
                reason,
            } = event
            {
                if *player != id {
                    return None;
                }
                let source = match reason {
                    VpReason::RoundTile { tile_id } => {
                        format!("라운드 목표 타일 {tile_id} · 광산마다 2점")
                    }
                    VpReason::TechTile { tile_id } => format!("기술 타일 {tile_id}"),
                    VpReason::FederationToken { token_kind } => format!("연방 토큰 {token_kind}"),
                    VpReason::RoundBooster { booster_id } => {
                        format!("부스터 {booster_id} 패스 보너스")
                    }
                    _ => format!("{reason:?}"),
                };
                Some(TutorialScore {
                    amount: *amount,
                    source,
                    reason: Some(reason.clone()),
                })
            } else {
                None
            }
        })
        .collect();
    let difference =
        after.players[0].vp - before.players[0].vp - scores.iter().map(|s| s.amount).sum::<i32>();
    if difference != 0 {
        let source = match action {
            GameAction::ChargePower { .. } => "파워 충전 비용",
            GameAction::ExploreSpaceship { .. }
            | GameAction::RoundBoosterRangeExploreSpaceship { .. } => "함선 탐사 비용",
            _ => "수입 점수 (IncomeReceived)",
        };
        scores.push(TutorialScore {
            amount: difference,
            source: source.into(),
            reason: None,
        });
    }
    scores
}

fn coord(q: i32, r: i32) -> HexCoord {
    HexCoord::new(q, r)
}
fn tech(id: u8) -> Option<TechTileChoice> {
    Some(TechTileChoice::Standard {
        tile: TechTile(id),
        advance_track: Some(if id == 10 {
            ResearchTrack::Economy
        } else {
            ResearchTrack::GaiaProject
        }),
        bonus_build_coord: None,
    })
}

pub fn steps() -> Vec<TutorialStep> {
    use GameAction::*;
    let actions = vec![
        ("1라운드 수입", "수입 받기를 누르세요.", "건물·연구·부스터·종족 보드의 수입을 실제로 받습니다.", "tutorial:income", ChooseIncomeOrder { charge_first: true }),
        (
            "광산 짓기",
            "(-1, 1)에 광산을 지으세요.",
            "얼음 행성: 삽 1단계 × 광석 3, 내 건물에서 2칸이라 QIC 1, 광산 건설 광석 1·크레딧 2를 냅니다.",
            "hex:-1,1",
            Build {
                coord: coord(-1, 1),
            },
        ),
        (
            "파워 충전",
            "파워 충전을 수락하세요.",
            "상대 A가 (-2, 0)에 광산을 지었습니다. 교역소 옆이라 1점을 내고 2파워를 충전합니다.",
            "charge",
            ChargePower { accept: true },
        ),
        (
            "교역소",
            "(-1, 1)의 광산을 교역소로 바꾸세요.",
            "상대 광산까지 1칸입니다. 2칸 이내라 교역소 비용이 광석 2·크레딧 6에서 광석 2·크레딧 3으로 줄어듭니다.",
            "hex:-1,1",
            Upgrade {
                coord: coord(-1, 1),
                to: StructureType::TradingStation,
                tech_tile_choice: None,
            },
        ),
        (
            "파워로 크레딧",
            "파워 1개를 크레딧으로 바꾸세요.",
            "3구역 파워를 쓰면 1구역으로 돌아갑니다. 자유 행동은 차례를 넘기지 않지만 교환 비율이 비쌉니다.",
            "free:PowerToCredit",
            FreeAction {
                kind: FreeActionKind::PowerToCredit,
                count: 1,
            },
        ),
        (
            "연구소와 기술",
            "(-1, 1)을 연구소로 바꾸고 파워 4 충전 기술(10)을 고르세요.",
            "연구소는 광석 3·크레딧 5. 위 줄 표준 기술은 바로 위 트랙만 올립니다. 이 기술은 경제 아래라 경제가 오릅니다. 아래 줄 3장은 아무 트랙이나 고릅니다. 연구소는 수입 지식을 늘립니다.",
            "hex:-1,1",
            Upgrade {
                coord: coord(-1, 1),
                to: StructureType::ResearchLab,
                tech_tile_choice: tech(10),
            },
        ),
        (
            "가이아 연구",
            "가이아 프로젝트 연구를 한 칸 올리세요.",
            "지식 4로 가이아 연구를 1→2단계로 올리고 파워 토큰 3개를 받습니다.",
            "research:GaiaProject",
            ResearchAdvance {
                track: ResearchTrack::GaiaProject,
            },
        ),
        (
            "가이아 프로젝트",
            "(0, -3)에 가이아 프로젝트를 시작하세요.",
            "가이아포머를 보내고 파워를 가이아 구역으로 옮깁니다.",
            "hex:0,-3",
            GaiaFormation {
                coord: coord(0, -3),
            },
        ),
        (
            "기술 특수 행동",
            "파워 4 충전 기술(10)의 행동을 쓰세요.",
            "이 특수 행동은 라운드마다 한 번 쓸 수 있습니다.",
            "tech:10",
            TechTileSpecialAction {
                tile: TechTileRef::Standard { tile: TechTile(10) },
            },
        ),
        (
            "파워 태우기",
            "2구역 파워를 한 번 태우세요.",
            "지금 3구역은 6파워입니다. 3파워를 광석 1로 바꾸면 3만 남아 공용 4파워 칸을 못 씁니다. 2구역 토큰 하나를 영원히 버려 하나를 3구역으로 보내면 교환 뒤 4가 남습니다.",
            "free:BurnPower",
            FreeAction {
                kind: FreeActionKind::BurnPower,
                count: 1,
            },
        ),
        (
            "자원 변환 묶음 · 광석",
            "파워 3개를 광석 1개로 바꾸세요.",
            "급할 때만 쓰는 비싼 교환입니다. 파워 3 → 광석 1, 바로 다음 공용 칸은 파워 4 → 광석 2입니다.",
            "free:PowerToOre",
            FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
        ),
        (
            "공용 파워 행동",
            "파워 4로 광석 2를 받는 공용 칸(3)을 쓰세요.",
            "공용 칸은 한 라운드에 한 명만 쓸 수 있습니다. 상대 B가 먼저 쓴 파워 4 → 크레딧 7 칸(4)은 이번 라운드에 다시 쓸 수 없습니다.",
            "power:3",
            PowerAction { id: 3, coord: None },
        ),
        (
            "연구판 고급 기술",
            "(3, -5)을 연구소로 바꾸고 과학 고급 기술로 10을 덮은 뒤 테라포밍을 올리세요.",
            "고급 기술 조건은 과학 4단계, 초록 연방 토큰 뒤집기, 표준 기술 덮기입니다. 덮는 타일과 무관하게 테라포밍을 올립니다. 광석 3 행동 기술(21)은 라운드당 1회입니다.",
            "hex:3,-5",
            Upgrade {
                coord: coord(3, -5),
                to: StructureType::ResearchLab,
                tech_tile_choice: Some(TechTileChoice::Advanced {
                    track: ResearchTrack::Science,
                    covered_tile: TechTile(10),
                    advance_track: Some(ResearchTrack::Terraforming),
                }),
            },
        ),
        (
            "고급 기술 광석 행동",
            "광석 3 행동 기술(21)을 쓰세요.",
            "라운드마다 한 번 광석 3개를 받습니다.",
            "advanced:21",
            TechTileSpecialAction { tile: TechTileRef::Advanced { tile: AdvancedTechTile(21) } },
        ),
        (
            "QIC로 거리 늘리기",
            "(5, -6)에 광산을 지으세요.",
            "항법 기본 거리를 넘으면 부족한 거리 2칸마다 QIC 1개를 냅니다. 광산 기본 비용 광석 1·크레딧 2도 냅니다.",
            "hex:5,-6",
            Build {
                coord: coord(5, -6),
            },
        ),
        (
            "의회",
            "(-1, -1)의 교역소를 의회로 바꾸세요.",
            "테란 의회 능력은 다음 가이아 단계에서 쓸 수 있습니다.",
            "hex:-1,-1",
            Upgrade {
                coord: coord(-1, -1),
                to: StructureType::PlanetaryInstitute,
                tech_tile_choice: None,
            },
        ),
        (
            "QIC 아카데미",
            "(-1, 1)을 QIC 아카데미로 바꾸고 광석 1·QIC 1 즉시 기술(4)을 고르세요.",
            "아카데미 비용은 광석 6·크레딧 6. 즉시 광석 1·QIC 1을 받고 라운드당 1회 QIC 행동을 엽니다.",
            "hex:-1,1",
            Upgrade {
                coord: coord(-1, 1),
                to: StructureType::Academy(AcademyType::Qic),
                tech_tile_choice: tech(4),
            },
        ),
        (
            "아카데미 행동",
            "아카데미의 QIC 행동을 쓰세요.",
            "QIC를 1개 얻고 사용 표시를 놓습니다.",
            "academy",
            AcademyQicAction,
        ),
        (
            "Twilight 탐사",
            "Twilight 함선을 탐사하세요.",
            "거리와 셔틀을 확인하고 탐사 비용 5점을 냅니다.",
            "ship:Twilight",
            ExploreSpaceship {
                ship: SpaceshipId::Twilight,
            },
        ),
        (
            "아티팩트 조사",
            "광석 3·크레딧 3 아티팩트(6)를 고르세요.",
            "Twilight를 탐사했으므로 파워 토큰 6개를 버리고 조사해 즉시 광석 3·크레딧 3을 받습니다.",
            "artifact:6",
            ExamineArtifact {
                artifact: ArtifactId(6),
                copy_federation_token_kind: None,
                bonus_build_coord: None,
                bonus_tech_tile: None,
                bonus_research_track: None,
            },
        ),
        (
            "부스터 함선 탐사",
            "+3 거리 탐사 부스터(8)로 T F Mars를 탐사하세요.",
            "+3 거리로 탐사합니다. 상대들은 이미 패스했습니다.",
            "ship:TFMars",
            RoundBoosterRangeExploreSpaceship {
                ship: SpaceshipId::TFMars,
            },
        ),
        (
            "함선 크레딧 행동",
            "크레딧 행동으로 (-4, 0)에 광산을 지으세요.",
            "크레딧 3으로 테라포밍 1단계를 받고 광산 비용도 냅니다.",
            "hex:-4,0",
            SpaceshipCreditTerraform {
                coord: coord(-4, 0),
            },
        ),
        (
            "세 번째 함선",
            "Eclipse를 탐사하세요.",
            "서로 다른 함선 3척은 확장 고급 기술의 조건입니다.",
            "ship:Eclipse",
            ExploreSpaceship {
                ship: SpaceshipId::Eclipse,
            },
        ),
        (
            "연방 만들기",
            "세 건물을 위성 2개로 잇고 7점·크레딧 6 연방 토큰(5)을 고르세요.",
            "의회 3 + 아카데미 3 + 광산 1 = 파워 7입니다. 위성마다 토큰 하나를 버립니다.",
            "federation",
            FormFederation {
                hexes: vec![coord(-1, -3), coord(-1, -1), coord(-1, 1)],
                satellite_hexes: vec![coord(-1, -2), coord(-1, 0)],
                token: FederationTokenChoice::Supply { kind: 5 },
                bonus_build_coord: None,
                bonus_tech_tile: None,
                bonus_research_track: None,
            },
        ),
        (
            "연방 보상 다시 받기",
            "Twilight에서 7점·크레딧 6 연방 토큰(5)의 효과를 다시 쓰세요.",
            "QIC 3으로 보상을 다시 받고 토큰 색은 유지합니다.",
            "ship:Twilight",
            TwilightReplayFederationToken {
                token_kind: 5,
                bonus_build_coord: None,
                bonus_tech_tile: None,
                bonus_research_track: None,
            },
        ),
        (
            "확장 고급 기술",
            "(2, -4)를 연구소로 바꾸고 연구소마다 패스 3점 기술(7)로 즉시 보상 기술(4)을 덮은 뒤 테라포밍을 올리세요.",
            "확장 고급 기술은 함선 3척, 초록 연방 토큰 뒤집기, 덮을 표준 기술이 필요합니다. 원하는 연구 트랙을 올립니다. 패스할 때 연구소마다 3점입니다.",
            "hex:2,-4",
            Upgrade {
                coord: coord(2, -4),
                to: StructureType::ResearchLab,
                tech_tile_choice: Some(TechTileChoice::LostFleetAdvanced {
                    covered_tile: TechTile(4),
                    advance_track: Some(ResearchTrack::Terraforming),
                }),
            },
        ),
        (
            "패스",
            "패스하고 지식 1 수입 부스터(1)를 고르세요.",
            "상대들은 이미 패스했습니다. 다음 라운드는 패스한 순서로 시작합니다.",
            "pass",
            Pass {
                booster_id: Some(1),
            },
        ),
    ];
    actions
        .into_iter()
        .map(
            |(title, instruction, reason, target, action)| TutorialStep {
                title: title.into(),
                instruction: instruction.into(),
                reason: reason.into(),
                target: target.into(),
                timings: effect_timings(&action),
                action,
            },
        )
        .collect()
}

pub fn initial_state(room_code: &str, ids: [PlayerId; 4]) -> Result<GameState, RuleError> {
    let setup =
        Randomizer::generate_setup(SEED).map_err(|e| RuleError::ActionNotAllowed(e.to_string()))?;
    let names = [
        "나",
        "튜토리얼 상대 A",
        "튜토리얼 상대 B",
        "튜토리얼 상대 C",
    ];
    let players: Vec<_> = ids
        .iter()
        .zip(names)
        .map(|(&id, name)| (id, name.to_owned()))
        .collect();
    let mut state = MapEngine::init_game_state(room_code, SEED, &players, &setup);
    for (&id, faction) in ids.iter().zip([
        FactionId::Terrans,
        FactionId::HadschHallas,
        FactionId::Geodens,
        FactionId::Nevlas,
    ]) {
        RuleEngine::apply_setup_action(&mut state, id, SetupAction::SelectFaction { faction })?;
    }
    state.phase = GamePhase::Setup(SetupPhase::Complete);
    state.round = 1;
    state.round_tiles[0] = RoundTile::from_id(1);
    state.boosters = vec![Booster(1), Booster(2), Booster(3)];
    state.tutorial = Some(TutorialState { script_id: SCRIPT_ID.into(), step: 1, steps: steps(), introduction: vec![
        "4인 + Lost Fleet, 테란으로 1라운드를 진행합니다. 종족·초기 배치·부스터 선택은 마쳤습니다.".into(),
        "원래 규칙에서는 받지 않는 것: 광석 13, 크레딧 19, 지식 7, QIC 8, 파워 1·2·3구역 각각 4·5·3개 (테란 기본 4·4·0에 토큰 4개 추가), 30점으로 시작합니다.".into(),
        "원래 규칙에서는 받지 않는 것: 초록 연방 토큰 4번 1개와 과학 연구 4단계를 미리 받습니다. 지급 토큰의 보상은 시작 자원에 포함했습니다.".into(),
        "원래 규칙에서는 받지 않는 것: 교역소 3개·광산 1개를 준비했습니다. 부스터 8, 광산마다 2점인 라운드 목표, 과학 고급 21·확장 고급 7을 고정했습니다.".into(),
        "상대 A는 광산, B는 파워 행동을 한 번씩 하고 모두 일찍 패스합니다. 모든 좌석의 자원은 상한 안에서 시작합니다.".into(),
        "라운드 점수는 매 라운드 목표 타일로 바로 받습니다. 마지막에는 최종 점수 타일 2개도 계산해 봅니다.".into(),
    ], opponents: Vec::new(), final_scores: None, final_tiles: Vec::new(), feedback: TutorialFeedback::default(), income: Vec::new() });
    for (index, player) in state.players.iter_mut().enumerate() {
        player.booster = Some(Booster([8, 4, 6, 7][index]));
        player.resources.ore = match index {
            0 => 13,
            1 => 10,
            _ => 4,
        };
        player.resources.credits = if index == 0 { 19 } else { 15 };
        player.resources.knowledge = if index == 0 { 7 } else { 3 };
        player.resources.qic = if index == 0 { 8 } else { 1 };
        player.resources.power.bowl1 = if index == 0 { 4 } else { 2 };
        player.resources.power.bowl2 = if index == 0 { 5 } else { 2 };
        player.resources.power.bowl3 = if index == 0 { 3 } else { 4 };
        player.vp = 30;
    }
    // Place the replacement standard tile under the same Gaia track as the old tile.
    for tile in state
        .research_board
        .tech_tiles
        .iter_mut()
        .chain(state.research_board.tech_tile_slots.iter_mut().flatten())
    {
        tile.0 = match tile.0 {
            4 => 7,
            7 => 4,
            other => other,
        };
    }
    state.research_board.advanced_tech_tiles[5] = Some(AdvancedTechTile(21));
    state.research_board.lost_fleet_advanced_tech_tile = Some(AdvancedTechTile(7));
    state.players[0].research_tracks.science = 4;
    state.players[0].federation_tokens.push(FederationToken(4));
    if let Some(index) = state
        .research_board
        .federation_tokens
        .iter()
        .position(|token| token.0 == 4)
    {
        state.research_board.federation_tokens.remove(index);
    }
    for player in &state.players {
        for track in ResearchTrack::all() {
            if let Some(area) = state.research_board.tracks.get_mut(&track) {
                area.player_levels
                    .insert(player.player_id, player.research_tracks.get(track));
            }
        }
    }
    for (seat, q, r, kind) in [
        (0, -1, -1, StructureType::TradingStation),
        (0, -1, -3, StructureType::Mine),
        (0, 3, -5, StructureType::TradingStation),
        (0, 2, -4, StructureType::TradingStation),
        (1, -3, 0, StructureType::Mine),
        (2, 4, -3, StructureType::Mine),
        (3, -7, 6, StructureType::Mine),
    ] {
        let hex = coord(q, r);
        state.players[seat].structures.push(Structure { hex, kind });
        let target = state
            .board
            .hexes
            .get_mut(&hex)
            .ok_or(RuleError::InvalidTarget(hex))?;
        target.structures.push(PlacedStructure {
            owner: ids[seat],
            kind,
        });
        if let Some(planet) = &mut target.planet {
            planet.owner = Some(ids[seat]);
            if seat == 0 {
                planet.planet_type = PlanetType::Terra;
            }
        }
    }
    if let Some(ship) = state
        .spaceship_boards
        .iter_mut()
        .find(|s| s.id == SpaceshipId::Twilight)
    {
        ship.artifact_pool = vec![ArtifactId(6), ArtifactId(2), ArtifactId(3), ArtifactId(4)];
    }
    Ok(state)
}

/// Opponents demonstrate one action each, then pass at their next opportunity.
fn opponent_action(_state: &GameState, seat: usize, step: usize) -> Result<GameAction, RuleError> {
    if seat == 1 && step == 2 {
        return Ok(GameAction::Build {
            coord: coord(-2, 0),
        });
    }
    if seat == 2 && step <= 3 {
        return Ok(GameAction::PowerAction { id: 4, coord: None });
    }
    Ok(GameAction::Pass {
        booster_id: Some(match seat {
            1 => 3,
            2 => 4,
            _ => 2,
        }),
    })
}

pub fn matches_action(expected: &GameAction, actual: &GameAction) -> bool {
    fn canonical(action: &GameAction) -> GameAction {
        let mut action = action.clone();
        if let GameAction::FormFederation {
            hexes,
            satellite_hexes,
            ..
        } = &mut action
        {
            hexes.sort_by_key(|hex| (hex.q, hex.r));
            satellite_hexes.sort_by_key(|hex| (hex.q, hex.r));
        }
        action
    }
    canonical(expected) == canonical(actual)
}

fn describe_move(state: &GameState, id: PlayerId, action: &GameAction) -> String {
    let name = state.player(id).map_or("상대", |p| p.nickname.as_str());
    let detail = match action {
        GameAction::Build { coord } => format!(
            "({}, {})에 광산을 지었습니다 → 파워 충전 기회",
            coord.q, coord.r
        ),
        GameAction::PowerAction { id: 4, .. } => "파워 4 → 크레딧 7 공용 칸을 사용했습니다".into(),
        GameAction::PowerAction { id, .. } => format!("공용 파워 {id}번을 사용했습니다"),
        GameAction::Pass { booster_id } => {
            format!("패스하고 부스터 {}을 골랐습니다", booster_id.unwrap_or(0))
        }
        GameAction::ChargePower { .. } => "파워 충전을 거절했습니다".into(),
        GameAction::FinishGaiaDecision => "가이아 단계를 마쳤습니다 (전환 생략)".into(),
        GameAction::ChooseIncomeOrder { .. } => "파워 충전부터 수입을 받았습니다".into(),
        _ => "행동을 마쳤습니다".into(),
    };
    format!("{name}: {detail}")
}

pub fn apply_step(
    state: &mut GameState,
    player: PlayerId,
    action: GameAction,
) -> Result<Vec<GameEvent>, RuleError> {
    let step = state.tutorial.as_ref().ok_or(RuleError::WrongPhase)?.step;
    let script = steps();
    let expected = script.get(step.saturating_sub(1));
    if player != state.players[0].player_id
        || expected.is_none_or(|s| !matches_action(&s.action, &action))
    {
        return Err(RuleError::TutorialStepMismatch(
            expected
                .map(|s| format!("지금은 {}", s.instruction))
                .unwrap_or_else(|| "튜토리얼을 마쳤습니다. 로비로 돌아가세요.".into()),
        ));
    }
    let mut next = state.clone();
    let mut opponents = Vec::new();
    let mut incomes = Vec::new();
    if step == 1 {
        incomes.push(income_breakdown(&next, 1));
    }
    let applied_action = action.clone();
    let mut pass = Vec::new();
    if let GameAction::Pass { booster_id } = &action {
        let labs = next.players[0]
            .structures
            .iter()
            .filter(|s| s.kind == StructureType::ResearchLab)
            .count();
        pass.push(format!(
            "고급 기술 7: 연구소 {labs}개 × 3점 = {}점",
            labs * 3
        ));
        pass.push(format!(
            "부스터 8 반납 (패스 점수 없음) → 부스터 {} 선택",
            booster_id.unwrap_or(0)
        ));
    }
    // The first card uses ChooseIncomeOrder as its transport intent. Setup::Complete
    // has no GameAction; the public transition validates the phase and applies income.
    let mut events = if step == 1 {
        RuleEngine::start_first_round(&mut next)?
    } else {
        RuleEngine::apply_action(&mut next, player, action)?
    };
    for _ in 0..100 {
        let pending = match &next.phase {
            GamePhase::ChargePowerPending { queue, .. } => queue
                .first()
                .map(|charge| (charge.player, GameAction::ChargePower { accept: false })),
            GamePhase::ActionPhase { active_player } => {
                let id = next.turn_order[*active_player];
                if id == player {
                    None
                } else {
                    let seat = next
                        .players
                        .iter()
                        .position(|p| p.player_id == id)
                        .ok_or(RuleError::WrongPhase)?;
                    Some((id, opponent_action(&next, seat, step)?))
                }
            }
            GamePhase::RoundScoring { .. } => {
                incomes.push(income_breakdown(&next, next.round + 1));
                events.extend(RuleEngine::advance_to_next_round(&mut next)?);
                continue;
            }
            GamePhase::GaiaDecisionPending { queue, .. } => queue
                .first()
                .map(|p| (p.player, GameAction::FinishGaiaDecision)),
            GamePhase::IncomeOrderPending { queue, .. } => queue.first().map(|p| {
                (
                    p.player,
                    GameAction::ChooseIncomeOrder { charge_first: true },
                )
            }),
            _ => None,
        };
        let Some((id, action)) = pending else { break };
        if step == 2 && id == player {
            break;
        }
        if next.round == 2 && matches!(next.phase, GamePhase::ActionPhase { .. }) {
            break;
        }
        opponents.push(TutorialMove {
            player: id,
            description: describe_move(&next, id, &action),
            action: action.clone(),
        });
        events.extend(RuleEngine::apply_action(&mut next, id, action)?);
    }
    let final_scores = (step == script.len())
        .then(|| crate::ScoringEngine::calculate_final_scoring_breakdown(&next));
    let final_tiles = if final_scores.is_some() {
        next.final_scoring_tiles
            .iter()
            .enumerate()
            .map(|(index, tile)| {
                let mut scoring_view = next.clone();
                let other = &mut scoring_view.final_scoring_tiles[1 - index];
                other.vp_1st = 0;
                other.vp_2nd = 0;
                other.vp_3rd = 0;
                TutorialFinalTile {
                    tile_id: tile.id,
                    scores: crate::ScoringEngine::calculate_final_scoring_breakdown(&scoring_view)
                        .map(|score| (score.player_id, score.final_tile_vp)),
                }
            })
            .collect()
    } else {
        Vec::new()
    };
    if !pass.is_empty() {
        pass.push(format!(
            "다음 라운드 순서: {}",
            next.turn_order
                .iter()
                .filter_map(|id| next.player(*id).map(|p| p.nickname.clone()))
                .collect::<Vec<_>>()
                .join(" → ")
        ));
    }
    let scores = score_feedback(state, &next, &applied_action, &events);
    if let Some(tutorial) = &mut next.tutorial {
        tutorial.feedback = TutorialFeedback { scores, pass };
        tutorial.income.extend(incomes);
        tutorial.final_tiles = final_tiles;
        tutorial.step = if final_scores.is_some() {
            script.len() + 2
        } else {
            step + 1
        };
        tutorial.opponents = opponents;
        tutorial.final_scores = final_scores;
    }
    *state = next;
    Ok(events)
}

#[cfg(test)]
#[allow(clippy::expect_used, clippy::unwrap_used)]
mod tests {
    use super::*;
    #[test]
    fn effect_timings_cover_actual_rewards_and_future_abilities() {
        let script = steps();
        let expected: &[&[&str]] = &[
            &["수입 때마다"],
            &["수입 때마다", "~할 때마다"],
            &["즉시 1회"],
            &["수입 때마다"],
            &["즉시 1회"],
            &["수입 때마다", "라운드당 1회 행동"],
            &["즉시 1회"],
            &["즉시 1회"],
            &["라운드당 1회 행동"],
            &["즉시 1회"],
            &["즉시 1회"],
            &["라운드당 1회 행동"],
            &["즉시 1회", "라운드당 1회 행동", "수입 때마다"],
            &["라운드당 1회 행동"],
            &["수입 때마다", "~할 때마다"],
            &["수입 때마다"],
            &["즉시 1회", "라운드당 1회 행동"],
            &["라운드당 1회 행동"],
            &["즉시 1회"],
            &["즉시 1회"],
            &["라운드당 1회 행동"],
            &["라운드당 1회 행동", "~할 때마다"],
            &["즉시 1회"],
            &["즉시 1회"],
            &["라운드당 1회 행동", "즉시 1회"],
            &["패스할 때", "수입 때마다"],
            &["패스할 때", "수입 때마다"],
        ];
        assert_eq!(script.len(), expected.len());
        for (step, expected) in script.iter().zip(expected) {
            assert_eq!(&step.timings, expected, "{}", step.title);
        }
        let mut kinds = Vec::new();
        for step in script {
            if let GameAction::FreeAction { kind, count } = step.action {
                assert!(
                    !kinds.contains(&kind),
                    "repeated conversion must be grouped"
                );
                if kind == FreeActionKind::KnowledgeToCredit {
                    assert_eq!(count, 2);
                }
                kinds.push(kind);
            }
        }
    }

    #[test]
    fn income_and_score_feedback_match_engine_events() {
        let mut state = initial_state("TUTOR", [0, 1, 2, 3]).expect("scenario");
        let mut rounds = Vec::new();
        let mut costs = 0;
        for step in steps() {
            let before = state.players[0].vp;
            let events = apply_step(&mut state, 0, step.action.clone()).expect("step");
            let tutorial = state.tutorial.as_ref().expect("tutorial");
            assert_eq!(
                tutorial
                    .feedback
                    .scores
                    .iter()
                    .map(|s| s.amount)
                    .sum::<i32>(),
                state.players[0].vp - before
            );
            for score in &tutorial.feedback.scores {
                if score.reason.is_none() {
                    assert!(matches!(
                        step.action,
                        GameAction::ChargePower { .. }
                            | GameAction::ExploreSpaceship { .. }
                            | GameAction::RoundBoosterRangeExploreSpaceship { .. }
                    ));
                    assert_eq!(score.amount, state.players[0].vp - before);
                    costs += 1;
                } else {
                    assert!(events.iter().any(|event| matches!(event, GameEvent::VpAwarded { player: 0, amount, reason } if *amount == score.amount && serde_json::to_value(reason).unwrap() == serde_json::to_value(&score.reason).unwrap())));
                }
            }
            for event in events {
                if let GameEvent::IncomeReceived {
                    player: 0,
                    round,
                    ore,
                    credits,
                    knowledge,
                    qic,
                    power_charge,
                    power_tokens,
                    vp,
                } = event
                {
                    let income = tutorial
                        .income
                        .iter()
                        .find(|i| i.round == round)
                        .expect("income card");
                    let total: [i32; 7] = std::array::from_fn(|index| {
                        income.rows.iter().map(|r| r.amounts[index]).sum()
                    });
                    assert_eq!(
                        total,
                        [ore, credits, knowledge, qic, power_charge, power_tokens, vp]
                            .map(i32::from),
                        "round {round}"
                    );
                    rounds.push(round);
                }
            }
        }
        assert_eq!(rounds, vec![1, 2]);
        assert_eq!(costs, 4);
        assert!(state.tutorial.as_ref().unwrap().feedback.pass[0].contains("2개 × 3점 = 6점"));
    }

    #[test]
    fn mismatched_actions_and_targets_leave_state_unchanged() {
        let mut state = initial_state("TUTOR", [0, 1, 2, 3]).expect("scenario");
        for (id, action) in [
            (0, GameAction::AcademyQicAction),
            (
                0,
                GameAction::Build {
                    coord: coord(5, -6),
                },
            ),
            (1, steps()[0].action.clone()),
        ] {
            let before = state.serialize();
            assert!(matches!(
                apply_step(&mut state, id, action),
                Err(RuleError::TutorialStepMismatch(_))
            ));
            assert_eq!(state.serialize(), before);
        }
    }

    #[test]
    fn browser_fixture_replays_the_shared_script() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "../../gaia-frontend/src/tests/fixtures/tutorial-round1.json"
        ))
        .expect("browser fixture");
        let mut state = initial_state("TUTOR", [0, 1, 2, 3]).expect("scenario");
        state.created_at = 0;
        let mut encoded = fixture["initial"].clone();
        assert_eq!(state.serialize(), encoded);
        for (index, step) in steps().into_iter().enumerate() {
            apply_step(&mut state, 0, step.action).expect("script step");
            for change in fixture["changes"][index].as_array().expect("changes") {
                let path = change["path"]
                    .as_array()
                    .expect("path")
                    .iter()
                    .map(|part| part.as_str().expect("key"))
                    .collect::<Vec<_>>()
                    .join("/");
                *encoded
                    .pointer_mut(&format!("/{path}"))
                    .expect("changed field") = change["value"].clone();
            }
            assert_eq!(
                state.serialize(),
                encoded,
                "browser fixture step {}",
                index + 1
            );
        }
    }

    fn assert_resource_caps(state: &GameState) {
        for player in &state.players {
            let resources = &player.resources;
            assert!(
                resources.ore <= Resources::ORE_CAP,
                "seat {} ore",
                player.player_id
            );
            assert!(
                resources.knowledge <= Resources::KNOWLEDGE_CAP,
                "seat {} knowledge",
                player.player_id
            );
            assert!(
                resources.credits <= Resources::CREDITS_CAP,
                "seat {} credits",
                player.player_id
            );
        }
    }

    #[test]
    fn replay_entire_round() {
        let mut state = initial_state("TUTOR", [0, 1, 2, 3]).expect("scenario");
        assert_resource_caps(&state);
        let mut direct = state.clone();
        let mut opponent_main_actions = [0; 4];
        for (index, step) in steps().into_iter().enumerate() {
            if matches!(
                step.action,
                GameAction::FreeAction {
                    kind: FreeActionKind::BurnPower,
                    ..
                }
            ) {
                assert_eq!(state.players[0].resources.power.bowl3, 6);
                let mut attempt = state.clone();
                RuleEngine::apply_action(
                    &mut attempt,
                    0,
                    GameAction::FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
                )
                .expect("ore conversion before burning");
                assert!(RuleEngine::apply_action(
                    &mut attempt,
                    0,
                    GameAction::PowerAction { id: 3, coord: None }
                )
                .is_err());
            }
            if index == 0 {
                RuleEngine::start_first_round(&mut direct).expect("first income");
            } else {
                RuleEngine::apply_action(&mut direct, 0, step.action.clone())
                    .expect("direct player action");
            }
            assert_resource_caps(&direct);

            apply_step(&mut state, 0, step.action)
                .unwrap_or_else(|e| panic!("step {}: {e}; phase {:?}", index + 1, state.phase));
            for movement in &state.tutorial.as_ref().expect("tutorial").opponents {
                if matches!(direct.phase, GamePhase::RoundScoring { .. }) {
                    RuleEngine::advance_to_next_round(&mut direct).expect("round transition");
                }
                RuleEngine::apply_action(&mut direct, movement.player, movement.action.clone())
                    .expect("direct scripted move");
                assert_resource_caps(&direct);
                assert!(!matches!(
                    movement.action,
                    GameAction::ResearchAdvance { .. }
                ));
                if matches!(
                    movement.action,
                    GameAction::Build { .. }
                        | GameAction::PowerAction { .. }
                        | GameAction::Pass { .. }
                ) {
                    opponent_main_actions[movement.player as usize] += 1;
                }
            }
            if matches!(direct.phase, GamePhase::RoundScoring { .. }) {
                RuleEngine::advance_to_next_round(&mut direct).expect("round transition");
            }
            assert_resource_caps(&state);
            if index >= 3 && state.round == 1 {
                assert!(state.players[1..].iter().all(|p| p.passed));
            }
            let mut actual = state.clone();
            actual.tutorial = None;
            let mut expected = direct.clone();
            expected.tutorial = None;
            assert_eq!(
                actual.serialize(),
                expected.serialize(),
                "step {} must only apply engine actions",
                index + 1
            );
        }
        assert_eq!(opponent_main_actions, [0, 2, 2, 1]);
        let player = &state.players[0];
        assert_eq!(player.advanced_tech_tiles.len(), 2);
        assert_eq!(player.gray_federation_tokens.len(), 2);
        assert!(player.federation_tokens.is_empty());
        assert_eq!(player.explored_ships, vec![0, 2, 3]);
        assert_eq!(player.covered_tech_tiles, vec![TechTile(10), TechTile(4)]);
        assert!(state.research_board.advanced_tech_tiles[5].is_none());
        assert!(state.research_board.lost_fleet_advanced_tech_tile.is_none());
        assert_eq!(
            state.tutorial.as_ref().expect("tutorial").final_scores,
            Some(crate::ScoringEngine::calculate_final_scoring_breakdown(
                &state
            ))
        );
        let scores = state
            .tutorial
            .as_ref()
            .expect("tutorial")
            .final_scores
            .expect("preview");
        for score in scores {
            let total: i32 = state
                .tutorial
                .as_ref()
                .expect("tutorial")
                .final_tiles
                .iter()
                .flat_map(|tile| tile.scores)
                .filter(|(id, _)| *id == score.player_id)
                .map(|(_, vp)| vp)
                .sum();
            assert_eq!(total, score.final_tile_vp);
        }
        assert_eq!(state.round, 2);
        assert!(matches!(state.phase, GamePhase::ActionPhase { .. }));
        assert_eq!(
            state.tutorial.as_ref().map(|t| t.step),
            Some(steps().len() + 2)
        );
        assert!(state.board.hexes[&coord(0, -3)]
            .planet
            .as_ref()
            .is_some_and(|p| p.is_gaia_formed));
    }
}
