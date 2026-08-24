use crate::data::sectors::load_sectors;
use crate::game_state::{
    BoardState, GamePhase, GameState, Hex, HexCoord, Planet, PlanetType, PlayerId, PlayerState,
    PowerCycle, ResearchBoard, ResearchTracks, Resources, RoomCode, RoundTile, Sector, SetupPhase,
    StructureType,
};
use crate::randomizer::{GameSetup, SectorPlacement};
use crate::setup_policy::SetupPolicy;
use std::collections::{HashMap, HashSet, VecDeque};
use std::time::{SystemTime, UNIX_EPOCH};

pub struct MapEngine;

impl MapEngine {
    /// BFS to find all hexes reachable within `range` steps from any of `start_hexes`,
    /// traversing only hexes present on the board.
    pub fn reachable_hexes(
        board: &BoardState,
        start_hexes: &[HexCoord],
        range: u8,
    ) -> HashSet<HexCoord> {
        let mut visited: HashMap<HexCoord, u8> = HashMap::new();
        let mut queue: VecDeque<(HexCoord, u8)> = VecDeque::new();

        for &start in start_hexes {
            if visited.get(&start).copied().unwrap_or(u8::MAX) > 0 {
                visited.insert(start, 0);
                queue.push_back((start, 0));
            }
        }

        while let Some((hex, dist)) = queue.pop_front() {
            if dist >= range {
                continue;
            }
            for neighbor in hex.neighbors() {
                if board.hexes.contains_key(&neighbor) {
                    let prev = visited.get(&neighbor).copied().unwrap_or(u8::MAX);
                    if dist + 1 < prev {
                        visited.insert(neighbor, dist + 1);
                        queue.push_back((neighbor, dist + 1));
                    }
                }
            }
        }

        visited.into_keys().collect()
    }

    /// BFS connectivity check: returns true if all `hexes` form a single connected component,
    /// where adjacency is defined as any two hexes that are neighbors on the board.
    pub fn is_connected(hexes: &[HexCoord]) -> bool {
        if hexes.is_empty() {
            return true;
        }
        let hex_set: HashSet<HexCoord> = hexes.iter().copied().collect();
        let mut visited: HashSet<HexCoord> = HashSet::new();
        let mut queue: VecDeque<HexCoord> = VecDeque::new();

        let start = match hexes.first() {
            Some(&h) => h,
            None => return true, // empty is vacuously connected
        };
        visited.insert(start);
        queue.push_back(start);

        while let Some(current) = queue.pop_front() {
            for neighbor in current.neighbors() {
                if hex_set.contains(&neighbor) && !visited.contains(&neighbor) {
                    visited.insert(neighbor);
                    queue.push_back(neighbor);
                }
            }
        }

        visited.len() == hex_set.len()
    }

    /// Sum of structure power values (excluding satellites) for a given set of hexes
    /// owned by `player`.
    pub fn federation_power(board: &BoardState, player: PlayerId, hexes: &[HexCoord]) -> u32 {
        hexes
            .iter()
            .flat_map(|h| board.hexes.get(h))
            .flat_map(|hex| &hex.structures)
            .filter(|s| s.owner == player && s.kind != StructureType::Satellite)
            .map(|s| s.kind.power_value())
            .sum()
    }

    /// The sector category (Standard/Deep Space) of the sector containing `hex`,
    /// or `None` if `hex` isn't covered by any placed sector (e.g. an Interspace
    /// tile, not yet modeled). Uses the same distance-to-origin approximation as
    /// `sector_hexes`.
    pub fn sector_category_at(
        board: &BoardState,
        hex: HexCoord,
    ) -> Option<crate::data::SectorCategory> {
        let sector = board
            .sectors
            .iter()
            .find(|s| hex.distance(&s.origin) <= 2)?;
        Some(crate::data::category_for_sector(sector.id))
    }

    /// Find all hexes in the board that belong to a given sector id.
    pub fn sector_hexes(board: &BoardState, sector_id: u8) -> Vec<HexCoord> {
        board
            .sectors
            .iter()
            .filter(|s| s.id == sector_id)
            .flat_map(|sector| {
                // A sector occupies the origin + its ring of 6 immediate neighbors + outer ring
                // The exact template is defined in sectors.toml; here we return the stored hexes.
                board
                    .hexes
                    .keys()
                    .filter(|&&h| {
                        // hex belongs to this sector if within 2 steps of sector origin
                        h.distance(&sector.origin) <= 2
                    })
                    .copied()
                    .collect::<Vec<_>>()
            })
            .collect()
    }

    /// Count distinct sectors containing at least one structure owned by `player`.
    pub fn sectors_occupied(board: &BoardState, player: PlayerId) -> usize {
        let mut sector_ids: HashSet<u8> = HashSet::new();
        for sector in &board.sectors {
            let has_structure = board.hexes.values().any(|hex| {
                hex.coord.distance(&sector.origin) <= 2
                    && hex.structures.iter().any(|s| s.owner == player)
            });
            if has_structure {
                sector_ids.insert(sector.id);
            }
        }
        sector_ids.len()
    }

    /// Expand a list of sector placements into a `BoardState` with all hexes populated.
    /// For double-sided sectors (id 5/6/7), uses side "A" by default if not specified.
    pub fn build_board(sector_layout: &[SectorPlacement]) -> BoardState {
        let sector_file = load_sectors();
        let mut hexes: HashMap<HexCoord, Hex> = HashMap::new();
        let mut sectors: Vec<Sector> = Vec::new();
        let mut lost_planet: Option<HexCoord> = None;

        for placement in sector_layout {
            let template = sector_file
                .sectors
                .iter()
                .find(|s| {
                    s.id == placement.sector_id && s.side.as_deref() == placement.side.as_deref()
                })
                .or_else(|| {
                    sector_file
                        .sectors
                        .iter()
                        .find(|s| s.id == placement.sector_id)
                });
            let Some(template) = template else {
                log::error!(
                    "sector template {} {:?} is missing from sectors.toml",
                    placement.sector_id,
                    placement.side
                );
                continue;
            };

            for hex_tmpl in &template.hexes {
                let rel = HexCoord::new(hex_tmpl.rel_q, hex_tmpl.rel_r);
                let world = rel.rotate_n(placement.rotation).add(&placement.origin);

                let planet = hex_tmpl
                    .planet
                    .as_deref()
                    .and_then(PlanetType::from_name)
                    .map(|pt| {
                        if pt == PlanetType::LostPlanet {
                            lost_planet = Some(world);
                        }
                        Planet {
                            planet_type: pt,
                            is_gaia_formed: false,
                            owner: None,
                        }
                    });

                hexes.insert(
                    world,
                    Hex {
                        coord: world,
                        planet,
                        space_tile_kind: None,
                        structures: Vec::new(),
                        satellites: Vec::new(),
                    },
                );
            }

            sectors.push(Sector {
                id: placement.sector_id,
                rotation: placement.rotation,
                origin: placement.origin,
            });
        }

        BoardState {
            sectors,
            hexes,
            lost_planet,
        }
    }

    /// Build an initial `GameState` from a `GameSetup` and the room's player list.
    /// The game is placed in sequential faction selection with clockwise room order.
    pub fn init_game_state(
        room_code: &str,
        players: &[(PlayerId, String)],
        setup: &GameSetup,
    ) -> GameState {
        let all_placements: Vec<SectorPlacement> = setup
            .sector_layout
            .iter()
            .chain(setup.deep_space_layout.iter())
            .cloned()
            .collect();
        let board = Self::build_board(&all_placements);

        let player_states: Vec<PlayerState> = players
            .iter()
            .map(|(id, nickname)| PlayerState {
                player_id: *id,
                nickname: nickname.clone(),
                faction: None,
                resources: Resources {
                    ore: 0,
                    credits: 0,
                    knowledge: 0,
                    qic: 0,
                    power: PowerCycle::zero(),
                    spent_gaia_formers: 0,
                },
                structures: Vec::new(),
                research_tracks: ResearchTracks::new(),
                vp: 10,
                passed: false,
                federation_tokens: Vec::new(),
                alliance_tiles: Vec::new(),
                explored_ships: Vec::new(),
                gaiaformers_total: 0,
                gaiaformers_deployed: 0,
                tech_tiles: Vec::new(),
                pi_ability_used: false,
                first_colonization_bonus_used: false,
                academy_qic_action_used_this_round: false,
            })
            .collect();

        let round_tile_ids = &setup.round_tile_ids;
        let round_tiles: [RoundTile; 6] =
            std::array::from_fn(|i| RoundTile::from_id(round_tile_ids[i]));

        let created_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();

        let player_order: Vec<PlayerId> = players.iter().map(|(id, _)| *id).collect();
        let faction_selection =
            SetupPolicy::initialize(player_order.clone(), setup.factions.clone());
        let phase = faction_selection
            .current_player()
            .map_or(GamePhase::Setup(SetupPhase::Complete), |active_player| {
                GamePhase::Setup(SetupPhase::FactionSelection { active_player })
            });

        GameState {
            room_code: RoomCode(room_code.to_string()),
            created_at,
            version: 0,
            round: 0,
            phase,
            players: player_states,
            board,
            round_tiles,
            boosters: setup.boosters.clone(),
            final_scoring_tiles: setup.final_scoring.clone(),
            research_board: {
                let mut rb = ResearchBoard::new();
                rb.tech_tiles = setup
                    .tech_tile_ids
                    .iter()
                    .map(|&id| crate::game_state::TechTile(id))
                    .collect();
                rb
            },
            faction_selection: Some(faction_selection),
            turn_order: player_order,
            current_player: 0,
            used_power_actions: Vec::new(),
            used_qic_action_slots: Vec::new(),
            event_log: Vec::new(),
        }
    }
}
