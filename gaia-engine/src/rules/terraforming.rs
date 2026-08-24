use crate::game_state::PlanetType;

// ── Planet ring ───────────────────────────────────────────────────────────────

/// The 7-planet cyclic ring used for terraforming distance calculation.
/// Adjacent entries cost 1 terraforming step to convert between.
pub const PLANET_RING: [PlanetType; 7] = [
    PlanetType::Terra,
    PlanetType::Swamp,
    PlanetType::Desert,
    PlanetType::Oxide,
    PlanetType::Titanium,
    PlanetType::Volcanic,
    PlanetType::Ice,
];

// ── Cost table ────────────────────────────────────────────────────────────────

/// Ore cost per terraforming step, indexed by research track level (0-5).
/// Levels 0-1 → 3 ore/step; level 2 → 2 ore/step; levels 3-5 → 1 ore/step.
const COST_PER_STEP: [u8; 6] = [3, 3, 2, 1, 1, 1];

// ── Public API ────────────────────────────────────────────────────────────────

/// Shortest-ring distance in steps between two planet types.
///
/// Returns `None` when either planet type is not on the standard ring
/// (Transdim, Gaia, LostPlanet, Asteroid, ProtoPlanet).
pub fn ring_distance(from: PlanetType, to: PlanetType) -> Option<u8> {
    let fi = PLANET_RING.iter().position(|&p| p == from)?;
    let ti = PLANET_RING.iter().position(|&p| p == to)?;
    let n = PLANET_RING.len();
    let fwd = (ti + n - fi) % n;
    let bwd = (fi + n - ti) % n;
    Some(fwd.min(bwd) as u8)
}

/// Ore cost for a given terraforming distance (in steps) at research track `level` (0-5).
pub fn cost_for_distance(distance: u8, track_level: u8) -> u8 {
    let level = (track_level as usize).min(COST_PER_STEP.len() - 1);
    distance * COST_PER_STEP[level]
}

/// Total ore cost to convert `from` into `to` given the player's
/// terraforming research track `level` (0-5).
///
/// Returns `0` for same-type conversions and `None` when either type
/// is outside the standard 7-planet ring.
pub fn get_terraforming_cost(from: PlanetType, to: PlanetType, track_level: u8) -> Option<u8> {
    if from == to {
        return Some(0);
    }
    let dist = ring_distance(from, to)?;
    Some(cost_for_distance(dist, track_level))
}

// ── Tests ─────────────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use PlanetType::*;

    #[test]
    fn ring_distance_adjacent() {
        assert_eq!(ring_distance(Terra, Swamp), Some(1));
        assert_eq!(ring_distance(Ice, Terra), Some(1)); // wraps around
    }

    #[test]
    fn ring_distance_symmetric() {
        assert_eq!(ring_distance(Terra, Oxide), ring_distance(Oxide, Terra));
    }

    #[test]
    fn cost_decreases_with_research() {
        let costs = (
            get_terraforming_cost(Terra, Oxide, 0),
            get_terraforming_cost(Terra, Oxide, 4),
        );
        assert!(matches!(costs, (Some(cost_l0), Some(cost_l4)) if cost_l4 < cost_l0));
    }

    #[test]
    fn same_type_is_free() {
        assert_eq!(get_terraforming_cost(Desert, Desert, 0), Some(0));
    }

    #[test]
    fn non_ring_returns_none() {
        assert_eq!(get_terraforming_cost(Terra, Transdim, 0), None);
        assert_eq!(get_terraforming_cost(Gaia, Terra, 0), None);
    }
}
