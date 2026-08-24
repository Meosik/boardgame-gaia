use gaia_engine::game_state::PlanetType;
use gaia_engine::rules::terraforming::{get_terraforming_cost, ring_distance};
use proptest::prelude::*;

fn arb_ring_planet() -> impl Strategy<Value = PlanetType> {
    prop_oneof![
        Just(PlanetType::Terra),
        Just(PlanetType::Swamp),
        Just(PlanetType::Desert),
        Just(PlanetType::Oxide),
        Just(PlanetType::Titanium),
        Just(PlanetType::Volcanic),
        Just(PlanetType::Ice),
    ]
}

proptest! {
    #[test]
    fn cost_is_symmetric(a in arb_ring_planet(), b in arb_ring_planet(), level in 0u8..=5u8) {
        let ab = get_terraforming_cost(a, b, level);
        let ba = get_terraforming_cost(b, a, level);
        prop_assert_eq!(ab, ba, "terraforming cost must be symmetric");
    }

    #[test]
    fn same_planet_costs_zero(p in arb_ring_planet(), level in 0u8..=5u8) {
        let cost = get_terraforming_cost(p, p, level);
        prop_assert_eq!(cost, Some(0));
    }

    #[test]
    fn ring_distance_is_at_most_3(a in arb_ring_planet(), b in arb_ring_planet()) {
        let dist = ring_distance(a, b);
        prop_assert!(dist.is_none_or(|d| d <= 3), "ring has 7 planets, max distance = 3");
    }

    #[test]
    fn higher_level_never_increases_cost(
        a in arb_ring_planet(),
        b in arb_ring_planet(),
        lo in 0u8..=4u8,
    ) {
        let hi = lo + 1;
        let cost_lo = get_terraforming_cost(a, b, lo);
        let cost_hi = get_terraforming_cost(a, b, hi);
        if let (Some(cl), Some(ch)) = (cost_lo, cost_hi) {
            prop_assert!(ch <= cl, "higher level should not cost more");
        }
    }
}
