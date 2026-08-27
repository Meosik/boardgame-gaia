use crate::bidding::BiddingPolicy;
use crate::data::sectors::{load_sectors, SectorFile};
use crate::error::RuleError;
use crate::game_state::{
    ArtifactId, BoardState, FederationToken, GamePhase, GameState, Hex, HexCoord, Planet,
    PlanetType, PlayerId, PlayerState, PowerCycle, ResearchBoard, ResearchTracks, Resources,
    RoomCode, RoundTile, Sector, SetupPhase, SpaceshipBoard, SpaceshipId, StructureType,
};
use crate::randomizer::{lost_fleet_sector_origins, GameSetup, Randomizer, SectorPlacement};
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

    /// BFS shortest distance (in hex steps) from any of `start_hexes` to `target`, bounded by
    /// `max_range` (returns `None` if `target` isn't reachable within that bound). Used to
    /// compute the exact QIC needed to extend range beyond a player's basic range — rulebook
    /// p.11 ("Build a Mine"): "you can spend any number of Q.I.C. to increase your range by
    /// two spaces for each Q.I.C. spent," confirmed by the worked example (Navigation level 2,
    /// basic range 2, spend 1 QIC -> range 4). The Lost Fleet expansion explicitly reuses this
    /// same rule for "Start a Gaia Project" and "Explore a Lost Fleet Spaceship".
    pub fn shortest_distance(
        board: &BoardState,
        start_hexes: &[HexCoord],
        target: HexCoord,
        max_range: u8,
    ) -> Option<u8> {
        if start_hexes.contains(&target) {
            return Some(0);
        }
        let mut visited: HashMap<HexCoord, u8> = HashMap::new();
        let mut queue: VecDeque<(HexCoord, u8)> = VecDeque::new();

        for &start in start_hexes {
            if visited.get(&start).copied().unwrap_or(u8::MAX) > 0 {
                visited.insert(start, 0);
                queue.push_back((start, 0));
            }
        }

        while let Some((hex, dist)) = queue.pop_front() {
            if dist >= max_range {
                continue;
            }
            for neighbor in hex.neighbors() {
                if !board.hexes.contains_key(&neighbor) {
                    continue;
                }
                let prev = visited.get(&neighbor).copied().unwrap_or(u8::MAX);
                if dist + 1 < prev {
                    visited.insert(neighbor, dist + 1);
                    if neighbor == target {
                        return Some(dist + 1);
                    }
                    queue.push_back((neighbor, dist + 1));
                }
            }
        }

        None
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

    /// Sum of structure power values for a given set of hexes owned by `player`. Satellites
    /// never contribute (rulebook p.14). Ivits' Space Stations are not a "structure" in the
    /// rulebook's sense (`StructureType::power_value` returns 0 for them, matching "a space
    /// station is not a structure, so placing one does not allow opponents to charge power")
    /// but still count as power value 1 specifically for federation purposes (Appendix I:
    /// "each space station counts as having a power value of one for its federation").
    pub fn federation_power(board: &BoardState, player: PlayerId, hexes: &[HexCoord]) -> u32 {
        hexes
            .iter()
            .flat_map(|h| board.hexes.get(h))
            .flat_map(|hex| &hex.structures)
            .filter(|s| s.owner == player && s.kind != StructureType::Satellite)
            .map(|s| {
                if s.kind == StructureType::SpaceStation {
                    1
                } else {
                    s.kind.power_value()
                }
            })
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
        let sector_id = Self::sector_id_at(board, hex)?;
        Some(crate::data::category_for_sector(sector_id))
    }

    /// The id of the Space/Deep Space sector containing `hex`. Interspace
    /// tiles intentionally return `None` because they are not sectors.
    pub fn sector_id_at(board: &BoardState, hex: HexCoord) -> Option<u8> {
        let sector = board
            .sectors
            .iter()
            .find(|s| hex.distance(&s.origin) <= 2)?;
        Some(sector.id)
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

    /// Inserts one sector placement's hexes into an existing board (used both by `build_board`'s
    /// initial full build and by `place_deep_space_sectors`, which merges its 8 sectors into an
    /// already-assembled standard-sector board). For double-sided sectors (id 5/6/7), uses side
    /// "A" by default if not specified.
    fn insert_sector(
        board: &mut BoardState,
        placement: &SectorPlacement,
        sector_file: &SectorFile,
    ) {
        let template = sector_file
            .sectors
            .iter()
            .find(|s| s.id == placement.sector_id && s.side.as_deref() == placement.side.as_deref())
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
            return;
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
                        board.lost_planet = Some(world);
                    }
                    Planet {
                        planet_type: pt,
                        is_gaia_formed: false,
                        owner: None,
                    }
                });

            let previous = board.hexes.insert(
                world,
                Hex {
                    coord: world,
                    planet,
                    space_tile_kind: None,
                    structures: Vec::new(),
                    satellites: Vec::new(),
                },
            );
            assert!(
                previous.is_none(),
                "sector {} {:?} overlaps another sector at ({}, {})",
                placement.sector_id,
                placement.side,
                world.q,
                world.r
            );
        }

        board.sectors.push(Sector {
            id: placement.sector_id,
            rotation: placement.rotation,
            origin: placement.origin,
        });
    }

    /// Expand a list of sector placements into a `BoardState` with all hexes populated.
    pub fn build_board(sector_layout: &[SectorPlacement]) -> BoardState {
        let mut board = BoardState {
            sectors: Vec::new(),
            hexes: HashMap::new(),
            lost_planet: None,
            spaceship_tiles: HashMap::new(),
        };
        let sector_file = load_sectors();
        for placement in sector_layout {
            Self::insert_sector(&mut board, placement, &sector_file);
        }
        board
    }

    /// The 19 hex offsets forming one Standard sector's footprint (`sectors.toml`: "STANDARD
    /// sectors (01-10): radius-2 axial grid, 19 hexes each") — all points within axial distance
    /// 2 of the origin.
    fn sector_disk_offsets() -> Vec<HexCoord> {
        let origin = HexCoord::new(0, 0);
        let mut offsets = Vec::with_capacity(19);
        for q in -2..=2 {
            for r in -2..=2 {
                let coord = HexCoord::new(q, r);
                if coord.distance(&origin) <= 2 {
                    offsets.push(coord);
                }
            }
        }
        offsets
    }

    /// True if two Standard sector origins are "tightly adjacent" per the Lost Fleet 4-player
    /// layout (`Randomizer::tight_sector_directions`) — sharing exactly 3 border hexes, matching
    /// the rulebook's "as per the base game" spacing.
    fn sectors_tight_adjacent(a: HexCoord, b: HexCoord) -> bool {
        let diff = HexCoord::new(b.q - a.q, b.r - a.r);
        crate::randomizer::tight_sector_directions()
            .into_iter()
            .any(|d| d.q == diff.q && d.r == diff.r)
    }

    /// Finds the Lost Fleet expansion's 10 Interspace tile holes (rulebook p.5, "this will
    /// create 10 holes around the inner sectors, each the size of one space"): for every
    /// "triangle" of 3 mutually tight-adjacent Standard sectors, the single hex adjacent to all
    /// 3 sector disks and contained in none of them — the natural gap at that triple-junction.
    /// Generic over whatever origins `board.sectors` actually holds (not hardcoded to a specific
    /// id assignment), so it stays correct regardless of which physical sector ended up where.
    /// See the plan this was implemented from for the geometric derivation (`rotate_60`-cycle
    /// canonical directions -> 2-center-domino-plus-8-ring topology -> exactly 10 triangles ->
    /// exactly 10 holes, verified computationally before writing this code).
    fn find_interspace_holes(board: &BoardState) -> Vec<HexCoord> {
        let origins: Vec<HexCoord> = board.sectors.iter().map(|s| s.origin).collect();
        let offsets = Self::sector_disk_offsets();
        let disks: Vec<HashSet<HexCoord>> = origins
            .iter()
            .map(|&o| offsets.iter().map(|d| o.add(d)).collect())
            .collect();
        let full_union: HashSet<HexCoord> = disks.iter().flatten().copied().collect();

        let n = origins.len();
        let mut adjacency: Vec<HashSet<usize>> = vec![HashSet::new(); n];
        for i in 0..n {
            for j in (i + 1)..n {
                if Self::sectors_tight_adjacent(origins[i], origins[j]) {
                    adjacency[i].insert(j);
                    adjacency[j].insert(i);
                }
            }
        }

        let mut holes = Vec::new();
        for i in 0..n {
            for &j in &adjacency[i] {
                if j <= i {
                    continue;
                }
                for &k in &adjacency[j] {
                    if k <= j || !adjacency[i].contains(&k) {
                        continue;
                    }
                    let mut boundary: HashSet<HexCoord> = HashSet::new();
                    for h in disks[i]
                        .iter()
                        .chain(disks[j].iter())
                        .chain(disks[k].iter())
                    {
                        for nb in h.neighbors() {
                            if !full_union.contains(&nb) {
                                boundary.insert(nb);
                            }
                        }
                    }
                    for cand in boundary {
                        let touches =
                            |d: &HashSet<HexCoord>| d.iter().any(|h| h.distance(&cand) == 1);
                        if touches(&disks[i]) && touches(&disks[j]) && touches(&disks[k]) {
                            holes.push(cand);
                            break;
                        }
                    }
                }
            }
        }
        holes
    }

    /// Real Lost Fleet Interspace-tile placement (rulebook p.4-5, "Interspace Tiles" + "Setup
    /// for 4 players"): fills the 10 natural gaps found by `find_interspace_holes` with the
    /// 4-player set's 10 physical tiles — 4 spaceship tiles (one per `SpaceshipId`), 4 Asteroid,
    /// 1 ProtoPlanet, 1 blank (composition confirmed by the user against their physical
    /// components, not printed anywhere in the rulebook PDF) — retrying the random assignment
    /// until "no two spaceship tiles are next to each other, i.e. a spaceship tile should not be
    /// within 3 spaces of another spaceship tile" holds (rulebook p.5). The blank tile is
    /// inserted as an empty walkable `Hex` (present in `board.hexes` so `reachable_hexes`/BFS
    /// treat it as passable connective space, matching every other "space" tile already on the
    /// board), not omitted.
    fn place_interspace_tiles(board: &mut BoardState, seed: &str) {
        #[derive(Clone, Copy)]
        enum Tile {
            Spaceship(SpaceshipId),
            Asteroid,
            ProtoPlanet,
            Blank,
        }

        let mut rng = Randomizer::new(seed);
        let holes = Self::find_interspace_holes(board);

        let mut pool: Vec<Tile> = SpaceshipId::all()
            .into_iter()
            .map(Tile::Spaceship)
            .collect();
        for _ in 0..4 {
            pool.push(Tile::Asteroid);
        }
        pool.push(Tile::ProtoPlanet);
        pool.push(Tile::Blank);

        let mut assignment: Vec<(HexCoord, Tile)> = Vec::new();
        const MAX_ATTEMPTS: u32 = 200;
        for attempt in 0..MAX_ATTEMPTS {
            let mut shuffled_holes = holes.clone();
            rng.shuffle(&mut shuffled_holes);
            let pairs: Vec<(HexCoord, Tile)> = shuffled_holes
                .into_iter()
                .zip(pool.iter().copied())
                .collect();

            let ship_coords: Vec<HexCoord> = pairs
                .iter()
                .filter_map(|&(coord, tile)| matches!(tile, Tile::Spaceship(_)).then_some(coord))
                .collect();
            let spaced_out = ship_coords
                .iter()
                .enumerate()
                .all(|(i, &a)| ship_coords[i + 1..].iter().all(|&b| a.distance(&b) >= 3));

            if spaced_out || attempt == MAX_ATTEMPTS - 1 {
                assignment = pairs;
                break;
            }
        }

        for (coord, tile) in assignment {
            let planet = match tile {
                Tile::Asteroid => Some(PlanetType::Asteroid),
                Tile::ProtoPlanet => Some(PlanetType::ProtoPlanet),
                Tile::Spaceship(_) | Tile::Blank => None,
            };
            board.hexes.insert(
                coord,
                Hex {
                    coord,
                    planet: planet.map(|planet_type| Planet {
                        planet_type,
                        is_gaia_formed: false,
                        owner: None,
                    }),
                    space_tile_kind: None,
                    structures: Vec::new(),
                    satellites: Vec::new(),
                },
            );
            if let Tile::Spaceship(ship) = tile {
                board.spaceship_tiles.insert(ship, coord);
            }
        }
    }

    /// Places the 8 Deep Space sectors (rulebook p.5: "place them with a random side up in the
    /// gaps along the outside edge of the gameboard") one per gap "between" each pair of
    /// tight-adjacent ring sectors around the Standard-sector assembly's outer perimeter — see
    /// `deep_space_gap_candidates`. Reuses `deep_space_layout`'s sector ids/sides (already
    /// shuffled deterministically in `Randomizer::build_setup`'s single PRNG stream) but computes
    /// fresh origins/rotations here, mirroring `place_interspace_tiles`'s established pattern of
    /// doing board-dependent placement after the board exists (`GameSetup.deep_space_layout`'s
    /// own origin/rotation values are placeholders, superseded by this).
    ///
    /// This replaces two earlier attempts, both found wrong by comparing against screenshots the
    /// project owner provided: (1) the original version picked the *first* valid boundary-
    /// adjacent `(anchor, rotation)` in shuffle order, with no constraint on *where* along the
    /// perimeter — reported as tiles clustering unevenly (two Deep Space tiles ending up next to
    /// the same Standard sector while other sectors bordered none) instead of one per gap between
    /// numbered sectors, "각 번호 우주 보드 사이에 위치하면 되는걸" (it should just sit between
    /// each numbered sector). (2) An attempt to fix that by maximizing shared-edge "snugness"
    /// instead just packed tiles into whichever spot fit tightest, regardless of *which* gap —
    /// checked against a reference randomizer tool (screenshot: sectors 11-18 each touching the
    /// board at only 1-2 hexes, evenly one per inter-sector gap) and reverted for over-nesting
    /// tiles into single tight pockets rather than spreading them around the perimeter. This
    /// version fixes the actual reported problem: it constrains the *set* of candidate anchors
    /// per Deep Space sector to the specific gap between one pair of adjacent Standard sectors,
    /// with a different pair assigned to each of the 8 sectors, guaranteeing even one-per-gap
    /// distribution around the whole perimeter by construction rather than by chance.
    fn place_deep_space_sectors(
        board: &BoardState,
        deep_space_layout: &[SectorPlacement],
        seed: &str,
    ) -> Vec<SectorPlacement> {
        let mut rng = Randomizer::new(seed);
        let template: [HexCoord; 3] = [
            HexCoord::new(0, 0),
            HexCoord::new(1, 0),
            HexCoord::new(0, 1),
        ];

        let mut occupied: HashSet<HexCoord> = board.hexes.keys().copied().collect();
        let mut gaps = Self::deep_space_gap_candidates();
        rng.shuffle(&mut gaps);

        let mut placements = Vec::with_capacity(deep_space_layout.len());
        for (entry, candidates) in deep_space_layout.iter().zip(gaps.iter()) {
            let mut placed = None;
            'search: for &anchor in candidates {
                for rotation in 0..6u8 {
                    let cells: [HexCoord; 3] =
                        std::array::from_fn(|i| template[i].rotate_n(rotation).add(&anchor));
                    if cells.iter().all(|c| !occupied.contains(c)) {
                        for c in cells {
                            occupied.insert(c);
                        }
                        placed = Some((anchor, rotation));
                        break 'search;
                    }
                }
            }
            let (origin, rotation) = placed.unwrap_or((entry.origin, entry.rotation));
            placements.push(SectorPlacement {
                sector_id: entry.sector_id,
                side: entry.side.clone(),
                origin,
                rotation,
            });
        }
        placements
    }

    /// The 8 candidate-anchor-hex lists for the 8 gaps "between" each pair of tight-adjacent ring
    /// sectors around the Standard-sector assembly's outer perimeter. `lost_fleet_sector_origins`
    /// gives the 10 origins as `[A, B, ring[0..8]]`, where `A`/`B` are the 2 fully-interior
    /// "center" sectors (surrounded on every side, so they never border the outside) and the 8
    /// ring positions form a single cycle of tight (distance-5, 3-hex-shared-border) adjacency —
    /// verified by brute-force pairwise distance search, not assumed: consecutive positions in
    /// `RING_CYCLE` are exactly the pairs at distance 5 from each other. For each such pair, the
    /// candidate hexes are every empty hex (outside all 10 Standard sectors' 19-hex disks) that
    /// touches *both* neighboring disks — the natural notch a Deep Space tile can bridge, giving
    /// every gap real contact with both of the sectors it sits between rather than a placement
    /// that could just as easily belong to only one of them. Purely geometric (depends only on
    /// which *origin positions* are cyclically adjacent, not on which sector id a game's shuffle
    /// put at each position), so this candidate set is identical every game — only which
    /// Deep Space sector id/side gets shuffled into which gap (`place_deep_space_sectors`) varies.
    fn deep_space_gap_candidates() -> [Vec<HexCoord>; 8] {
        const RING_CYCLE: [usize; 8] = [0, 1, 2, 3, 4, 7, 5, 6];

        let origins = lost_fleet_sector_origins();
        let ring: [HexCoord; 8] = std::array::from_fn(|i| origins[2 + i]);
        let cycle: [HexCoord; 8] = std::array::from_fn(|i| ring[RING_CYCLE[i]]);

        let disk = |center: HexCoord| -> HashSet<HexCoord> {
            let mut cells = HashSet::new();
            for dq in -2..=2i32 {
                for dr in -2..=2i32 {
                    let candidate = HexCoord::new(center.q + dq, center.r + dr);
                    if center.distance(&candidate) <= 2 {
                        cells.insert(candidate);
                    }
                }
            }
            cells
        };
        let all_disks: Vec<HashSet<HexCoord>> = origins.iter().map(|&o| disk(o)).collect();
        let all_occupied: HashSet<HexCoord> = all_disks.iter().flatten().copied().collect();

        std::array::from_fn(|i| {
            let d1 = disk(cycle[i]);
            let d2 = disk(cycle[(i + 1) % 8]);
            let mut candidates = Vec::new();
            for hex in d1.iter().chain(d2.iter()) {
                for n in hex.neighbors() {
                    if !all_occupied.contains(&n)
                        && !candidates.contains(&n)
                        && n.neighbors().iter().any(|x| d1.contains(x))
                        && n.neighbors().iter().any(|x| d2.contains(x))
                    {
                        candidates.push(n);
                    }
                }
            }
            candidates
        })
    }

    /// The 4 Lost Fleet spaceship boards' initial shared state — empty shuttle slots (one per
    /// possible player; per-slot power charge confirmed via a physical board photo, see
    /// `spaceship_shuttle_power_charge` in rules/engine.rs), Twilight's Artifact pool seeded
    /// with ids 1-9 and 11-13 (12 of the 13 physical Artifact tokens whose effects are confirmed
    /// — see `artifact_effect` in rules/engine.rs; id 10, "Copy the effect of a Federation Token
    /// you own," is deliberately excluded — it needs a federation-token-effect-replay mechanic
    /// that doesn't exist anywhere in the engine yet, so it must never actually be drawable until
    /// that infrastructure lands), and one Lost Fleet Federation token per ship (expansion p.5,
    /// "Take 4 of the new Federation tokens and distribute them on the 4 spaceships at random" —
    /// ids 8-15 in `federation_token_kind`, rules/engine.rs, one physical token each per the
    /// user's direct component check; 4 of the 8 are drawn into play, the rest return to the box).
    pub fn initial_spaceship_boards(seed: &str) -> Vec<SpaceshipBoard> {
        let mut rng = Randomizer::new(seed);
        let mut federation_pool: Vec<FederationToken> = (8..=15).map(FederationToken).collect();
        rng.shuffle(&mut federation_pool);

        SpaceshipId::all()
            .into_iter()
            .enumerate()
            .map(|(i, id)| SpaceshipBoard {
                id,
                explorers: vec![None; 4],
                artifact_pool: if id == SpaceshipId::Twilight {
                    (1..=13).map(ArtifactId).collect()
                } else {
                    Vec::new()
                },
                federation_token: federation_pool.get(i).cloned(),
            })
            .collect()
    }

    /// Build an initial `GameState` from a `GameSetup` and the room's player list.
    /// The game is placed in sequential faction selection with clockwise room order.
    ///
    /// `room_code` and `seed` are deliberately separate, even though every caller today happens
    /// to have both available: `room_code` only ever populates `GameState.room_code` (identity —
    /// never changes for a room's lifetime), while `seed` drives every RNG use in this function
    /// (Interspace/Deep Space placement, federation token shuffle, spaceship board init) —
    /// callers must pass the room's *current, reroll-able* `room.seed` for that, not the room
    /// code itself, or rerolling the setup would never actually move these positions/shuffles
    /// (this was a real bug: every call site used to pass the room code for both purposes).
    pub fn init_game_state(
        room_code: &str,
        seed: &str,
        players: &[(PlayerId, String)],
        setup: &GameSetup,
    ) -> GameState {
        let mut board = Self::build_board(&setup.sector_layout);
        Self::place_interspace_tiles(&mut board, seed);
        let deep_space_placements =
            Self::place_deep_space_sectors(&board, &setup.deep_space_layout, seed);
        let sector_file = load_sectors();
        for placement in &deep_space_placements {
            Self::insert_sector(&mut board, placement, &sector_file);
        }

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
                artifact_mines: Vec::new(),
                research_tracks: ResearchTracks::new(),
                vp: 10,
                setup_bid_vp: 0,
                passed: false,
                booster: None,
                federation_tokens: Vec::new(),
                gray_federation_tokens: Vec::new(),
                alliance_tiles: Vec::new(),
                explored_ships: Vec::new(),
                exploration_shuttles_available: 3,
                gaiaformers_total: 0,
                gaiaformers_deployed: 0,
                gaiaformers_in_gaia_area: 0,
                tech_tiles: Vec::new(),
                advanced_tech_tiles: Vec::new(),
                covered_tech_tiles: Vec::new(),
                pi_ability_used: false,
                first_colonization_bonus_used: false,
                academy_qic_action_used_this_round: false,
                gleens_special_action_used_this_round: false,
                space_giants_special_action_used_this_round: false,
                round_booster_special_action_used_this_round: false,
                faction_special_action_used_this_round: false,
                geodens_rewarded_planet_types: Vec::new(),
                federated_hexes: Vec::new(),
                tinkeroids_tiles_used: Vec::new(),
                moweyds_power_ring_hexes: Vec::new(),
                tech_tile_special_actions_used_this_round: Vec::new(),
                advanced_tech_tile_special_actions_used_this_round: Vec::new(),
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
                // One Advanced Tech tile per research track (`ResearchTrack::all()` order,
                // rulebook p.4: "Randomly place one advanced tech tile faceup on each space
                // between level 4 and 5 of the six research areas").
                for (index, &id) in setup.advanced_tech_tile_ids.iter().take(6).enumerate() {
                    rb.advanced_tech_tiles[index] = Some(crate::game_state::AdvancedTechTile(id));
                }
                // Base game Federation token supply (rulebook p.2 components): 19 tokens across
                // 7 reward kinds (`federation_token_kind` in rules/engine.rs) — 12 VP x3; 8 VP +
                // 1 ore x3; 8 VP + 2 power x3; 7 VP + 2 ore x3; 7 VP + 6 credits x3; 6 VP + 2
                // knowledge x3; 1 ore + 1 knowledge + 2 credits (no VP) x1.
                let mut federation_tokens: Vec<FederationToken> =
                    [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 6, 6, 6, 7]
                        .into_iter()
                        .map(FederationToken)
                        .collect();
                Randomizer::new(seed).shuffle(&mut federation_tokens);
                rb.federation_tokens = federation_tokens;
                rb
            },
            faction_selection: Some(faction_selection),
            bidding: None,
            turn_order: player_order,
            current_player: 0,
            used_power_actions: Vec::new(),
            spaceship_boards: Self::initial_spaceship_boards(seed),
            used_spaceship_actions: Vec::new(),
            event_log: Vec::new(),
        }
    }

    /// Build an initial game using the fixed four-player bidding setup.
    /// `setup.factions` must already contain the randomizer's four offered
    /// individual factions; the first room player is treated as the host.
    pub fn init_game_state_with_bidding(
        room_code: &str,
        seed: &str,
        players: &[(PlayerId, String)],
        setup: &GameSetup,
    ) -> Result<GameState, RuleError> {
        let mut state = Self::init_game_state(room_code, seed, players, setup);
        let player_order: Vec<PlayerId> = players.iter().map(|(id, _)| *id).collect();
        let bidding = BiddingPolicy::initialize(player_order.clone(), setup.factions.clone())?;
        let active_player = bidding
            .current_actor()
            .ok_or_else(|| RuleError::ActionNotAllowed("empty bidding setup".to_string()))?;

        state.phase = GamePhase::Setup(SetupPhase::Bidding { active_player });
        state.faction_selection = None;
        state.bidding = Some(bidding);
        state.turn_order = player_order;
        Ok(state)
    }
}
