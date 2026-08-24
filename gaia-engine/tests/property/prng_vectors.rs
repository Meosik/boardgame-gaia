/// Cross-language PRNG reproducibility tests.
///
/// Instead of hardcoding expected float values (which are fragile and require
/// running the JS reference implementation), we validate the structural
/// invariants that any correct Mulberry32-variant PRNG must satisfy.
///
/// True cross-language vector tests should be added separately once the
/// JS test harness can emit known-good seed→output pairs.
use gaia_engine::Randomizer;

#[test]
fn same_seed_same_sequence() {
    let values_a: Vec<f64> = {
        let mut rng = Randomizer::new("cross-lang-seed");
        (0..20).map(|_| rng.random()).collect()
    };
    let values_b: Vec<f64> = {
        let mut rng = Randomizer::new("cross-lang-seed");
        (0..20).map(|_| rng.random()).collect()
    };
    assert_eq!(
        values_a, values_b,
        "same seed must produce identical sequence"
    );
}

#[test]
fn different_seeds_differ() {
    let a: Vec<f64> = {
        let mut rng = Randomizer::new("seed-alpha");
        (0..10).map(|_| rng.random()).collect()
    };
    let b: Vec<f64> = {
        let mut rng = Randomizer::new("seed-beta");
        (0..10).map(|_| rng.random()).collect()
    };
    // Extremely unlikely to match with a good hash function
    let any_differ = a.iter().zip(b.iter()).any(|(x, y)| x != y);
    assert!(
        any_differ,
        "different seeds should produce different sequences"
    );
}

#[test]
fn output_in_unit_interval() {
    let mut rng = Randomizer::new("unit-interval-test");
    for i in 0..10_000 {
        let v = rng.random();
        assert!(
            (0.0..1.0).contains(&v),
            "random() output {v} out of [0.0,1.0) at step {i}"
        );
    }
}

#[test]
fn shuffle_preserves_all_elements() {
    let original = vec![1u32, 2, 3, 4, 5, 6, 7, 8];
    let mut shuffled = original.clone();
    let mut rng = Randomizer::new("shuffle-preservation");
    rng.shuffle(&mut shuffled);
    let mut sorted = shuffled.clone();
    sorted.sort();
    assert_eq!(sorted, original, "shuffle must preserve all elements");
}

#[test]
fn shuffle_single_element_unchanged() {
    let mut v = vec![42u32];
    let mut rng = Randomizer::new("single-element");
    rng.shuffle(&mut v);
    assert_eq!(v, vec![42]);
}

#[test]
fn shuffle_empty_no_panic() {
    let mut v: Vec<u32> = vec![];
    let mut rng = Randomizer::new("empty-shuffle");
    rng.shuffle(&mut v);
    assert!(v.is_empty());
}

#[test]
fn random_int_within_range() {
    let mut rng = Randomizer::new("random-int-range");
    for n in [1usize, 4, 7, 9, 100] {
        for _ in 0..1000 {
            let r = rng.random_int(n);
            assert!(r < n, "random_int({n}) returned {r} which is out of range");
        }
    }
}

#[test]
fn utf16_seed_encoding_known_ascii() {
    // For ASCII characters, UTF-16 code points == UTF-8 code points.
    // Two ASCII seeds that differ by one character must differ in output.
    let mut rng_a = Randomizer::new("a");
    let mut rng_b = Randomizer::new("b");
    assert_ne!(
        rng_a.random(),
        rng_b.random(),
        "ASCII seeds 'a' and 'b' must differ"
    );
}
