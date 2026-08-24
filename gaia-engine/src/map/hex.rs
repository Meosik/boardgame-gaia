use crate::game_state::HexCoord;

pub const DIRECTIONS: [HexCoord; 6] = [
    HexCoord { q: 1, r: 0 },
    HexCoord { q: -1, r: 0 },
    HexCoord { q: 0, r: 1 },
    HexCoord { q: 0, r: -1 },
    HexCoord { q: 1, r: -1 },
    HexCoord { q: -1, r: 1 },
];

/// Apply sector rotation (0-5 steps of 60°) to a relative hex coordinate.
pub fn apply_sector_rotation(hex: HexCoord, rotation: u8) -> HexCoord {
    hex.rotate_n(rotation)
}

/// All hexes within `range` steps of `origin` via BFS.
pub fn hexes_in_range(origin: HexCoord, range: u8) -> Vec<HexCoord> {
    if range == 0 {
        return vec![origin];
    }
    let mut result = Vec::new();
    let r = range as i32;
    for dq in -r..=r {
        let r_min = (-r).max(-dq - r);
        let r_max = r.min(-dq + r);
        for dr in r_min..=r_max {
            result.push(HexCoord::new(origin.q + dq, origin.r + dr));
        }
    }
    result
}
