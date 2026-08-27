use gaia_engine::game_state::PowerCycle;
use proptest::prelude::*;

fn arb_power_cycle() -> impl Strategy<Value = PowerCycle> {
    (0u8..=12, 0u8..=12, 0u8..=12, 0u8..=6).prop_map(|(b1, b2, b3, gaia)| PowerCycle {
        bowl1: b1,
        bowl2: b2,
        bowl3: b3,
        gaia_bowl: gaia,
        gaia_forming: 0,
        brainstone: None,
    })
}

proptest! {
    #[test]
    fn total_is_sum_of_bowls(cycle in arb_power_cycle()) {
        let expected = cycle.bowl1 as u16
            + cycle.bowl2 as u16
            + cycle.bowl3 as u16
            + cycle.gaia_bowl as u16
            + cycle.gaia_forming as u16
            + u16::from(cycle.brainstone.is_some());
        prop_assert_eq!(cycle.total() as u16, expected);
    }
}

// Not a property test (no generator input) — the `proptest!` macro's grammar
// requires every item to have a `pat in strategy` parameter list, so a plain
// zero-arg `#[test]` inside the same block fails to parse.
#[test]
fn zero_cycle_total_is_zero() {
    let z = PowerCycle::zero();
    assert_eq!(z.total(), 0);
}
