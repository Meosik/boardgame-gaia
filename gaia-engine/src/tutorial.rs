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
        (
            "광산 짓기",
            "(-1, 1)에 광산을 지으세요.",
            "얼음 행성을 테라포밍 1단계로 바꾸며 광석을 냅니다.",
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
            "상대 건물이 가까워 크레딧 비용이 할인됩니다.",
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
            "자유 행동은 차례를 넘기지 않습니다.",
            "free:PowerToCredit",
            FreeAction {
                kind: FreeActionKind::PowerToCredit,
                count: 1,
            },
        ),
        (
            "자원 변환 묶음 · 광석 1/5",
            "파워 3개를 광석 1개로 바꾸세요.",
            "시작 광석은 상한 15입니다. 건설에 필요한 광석을 변환으로 보충하며 차례는 유지됩니다.",
            "free:PowerToOre",
            FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
        ),
        (
            "자원 변환 묶음 · 광석 2/5",
            "파워 3개를 광석 1개로 바꾸세요.",
            "시작 광석은 상한 15입니다. 건설에 필요한 광석을 변환으로 보충하며 차례는 유지됩니다.",
            "free:PowerToOre",
            FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
        ),
        (
            "자원 변환 묶음 · 광석 3/5",
            "파워 3개를 광석 1개로 바꾸세요.",
            "시작 광석은 상한 15입니다. 건설에 필요한 광석을 변환으로 보충하며 차례는 유지됩니다.",
            "free:PowerToOre",
            FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
        ),
        (
            "자원 변환 묶음 · 광석 4/5",
            "파워 3개를 광석 1개로 바꾸세요.",
            "시작 광석은 상한 15입니다. 건설에 필요한 광석을 변환으로 보충하며 차례는 유지됩니다.",
            "free:PowerToOre",
            FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
        ),
        (
            "자원 변환 묶음 · 광석 5/5",
            "파워 3개를 광석 1개로 바꾸세요.",
            "시작 광석은 상한 15입니다. 건설에 필요한 광석을 변환으로 보충하며 차례는 유지됩니다.",
            "free:PowerToOre",
            FreeAction { kind: FreeActionKind::PowerToOre, count: 1 },
        ),
        (
            "자원 변환 묶음 · 지식",
            "지식 1개를 크레딧 1개로 바꾸세요.",
            "세 종류의 변환을 해 보았습니다. 오른쪽 자유 행동 목록에서 전체 변환 비율을 확인하세요.",
            "free:KnowledgeToCredit",
            FreeAction { kind: FreeActionKind::KnowledgeToCredit, count: 1 },
        ),
        (
            "연구소와 기술",
            "(-1, 1)을 연구소로 바꾸고 기술 10을 고르세요.",
            "기술 타일 아래의 경제 연구도 한 칸 오릅니다.",
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
            "파워 태우기",
            "2구역 파워를 한 번 태우세요.",
            "3구역은 3파워라 다음 4파워 행동을 못 합니다. 2구역 토큰 2개 중 하나를 영원히 버리고 하나를 3구역으로 옮겨 4파워를 만드세요.",
            "free:BurnPower",
            FreeAction {
                kind: FreeActionKind::BurnPower,
                count: 1,
            },
        ),
        (
            "공용 파워 행동",
            "공용 파워 행동 3번을 쓰세요.",
            "공용 칸은 한 라운드에 한 명만 쓸 수 있습니다. 상대 B가 먼저 쓴 4번은 이번 라운드에 다시 쓸 수 없습니다.",
            "power:3",
            PowerAction { id: 3, coord: None },
        ),
        (
            "기술 특수 행동",
            "기술 10의 파워 4 충전을 쓰세요.",
            "이 특수 행동은 라운드마다 한 번 쓸 수 있습니다.",
            "tech:10",
            TechTileSpecialAction {
                tile: TechTileRef::Standard { tile: TechTile(10) },
            },
        ),
        (
            "QIC로 거리 늘리기",
            "(5, -6)에 광산을 지으세요.",
            "기본 거리 밖이라 필요한 QIC를 자동으로 냅니다.",
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
            "(-1, 1)을 QIC 아카데미로 바꾸고 기술 7을 고르세요.",
            "지식 아카데미와 달리 매 라운드 QIC 행동을 얻습니다.",
            "hex:-1,1",
            Upgrade {
                coord: coord(-1, 1),
                to: StructureType::Academy(AcademyType::Qic),
                tech_tile_choice: tech(7),
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
            "아티팩트 6을 고르세요.",
            "Twilight를 탐사했으므로 파워 토큰 6개를 버리고 조사할 수 있습니다.",
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
            "부스터 8로 T F Mars를 탐사하세요.",
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
            "세 건물을 위성 2개로 잇고 연방 토큰 5을 고르세요.",
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
            "Twilight에서 연방 토큰 5을 다시 쓰세요.",
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
            "연구판 고급 기술",
            "(3, -5)을 연구소로 바꾸고 과학 고급 기술로 10을 덮은 뒤 테라포밍을 올리세요.",
            "과학 4단계와 초록 연방 토큰이 필요합니다. 토큰은 회색이 됩니다.",
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
            "확장 고급 기술",
            "(2, -4)를 연구소로 바꾸고 확장 고급 기술로 7을 덮은 뒤 테라포밍을 올리세요.",
            "함선 3척과 초록 연방 토큰이 필요합니다. 두 번째 토큰도 회색이 됩니다.",
            "hex:2,-4",
            Upgrade {
                coord: coord(2, -4),
                to: StructureType::ResearchLab,
                tech_tile_choice: Some(TechTileChoice::LostFleetAdvanced {
                    covered_tile: TechTile(7),
                    advance_track: Some(ResearchTrack::Terraforming),
                }),
            },
        ),
        (
            "패스",
            "패스하고 부스터 1을 고르세요.",
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
    state.phase = GamePhase::ActionPhase { active_player: 0 };
    state.round = 1;
    state.boosters = vec![Booster(1), Booster(2), Booster(3)];
    state.tutorial = Some(TutorialState { script_id: SCRIPT_ID.into(), step: 1, steps: steps(), introduction: vec![
        "4인 + Lost Fleet, 테란으로 1라운드를 진행합니다. 종족·초기 배치·부스터 선택은 마쳤습니다.".into(),
        "원래 규칙에서는 받지 않는 것: 광석 15, 크레딧 30, 지식 15, QIC 8, 파워 1·2·3구역 각각 2·2·19개, 30점으로 시작합니다.".into(),
        "원래 규칙에서는 받지 않는 것: 초록 연방 토큰 4번 1개와 과학 연구 4단계를 미리 받습니다. 지급 토큰의 보상은 시작 자원에 포함했습니다.".into(),
        "원래 규칙에서는 받지 않는 것: 교역소 3개·광산 1개를 준비했습니다. 부스터 8과 고정 맵을 사용합니다.".into(),
        "상대 A는 광산, B는 파워 행동을 한 번씩 하고 모두 일찍 패스합니다. 모든 좌석의 자원은 상한 안에서 시작합니다.".into(),
        "라운드 점수는 매 라운드 목표 타일로 바로 받습니다. 마지막에는 최종 점수 타일 2개도 계산해 봅니다.".into(),
    ], opponents: Vec::new(), final_scores: None, final_tiles: Vec::new() });
    for (index, player) in state.players.iter_mut().enumerate() {
        player.booster = Some(Booster([8, 4, 6, 7][index]));
        player.resources.ore = match index {
            0 => 15,
            1 => 10,
            _ => 4,
        };
        player.resources.credits = if index == 0 { 30 } else { 15 };
        player.resources.knowledge = if index == 0 { 15 } else { 3 };
        player.resources.qic = if index == 0 { 8 } else { 1 };
        // Terrans need 19 charged tokens for conversions and the power action,
        // plus four tokens to demonstrate charging and burning (23 total).
        player.resources.power.bowl1 = 2;
        player.resources.power.bowl2 = 2;
        player.resources.power.bowl3 = if index == 0 { 19 } else { 4 };
        player.vp = 30;
    }
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
    if seat == 1 && step == 1 {
        return Ok(GameAction::Build {
            coord: coord(-2, 0),
        });
    }
    if seat == 2 && step <= 2 {
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
    let mut events = RuleEngine::apply_action(&mut next, player, action)?;
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
        if step == 1 && id == player {
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
    if let Some(tutorial) = &mut next.tutorial {
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
#[allow(clippy::expect_used)]
mod tests {
    use super::*;
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
                assert_eq!(state.players[0].resources.power.bowl3, 3);
                let mut attempt = state.clone();
                assert!(RuleEngine::apply_action(
                    &mut attempt,
                    0,
                    GameAction::PowerAction { id: 3, coord: None }
                )
                .is_err());
            }
            RuleEngine::apply_action(&mut direct, 0, step.action.clone())
                .expect("direct player action");
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
            if index >= 2 && state.round == 1 {
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
        assert_eq!(player.covered_tech_tiles, vec![TechTile(10), TechTile(7)]);
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
