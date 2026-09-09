use gaia_engine::data::load_sectors;
use std::collections::HashMap;

#[test]
fn deep_space_planet_layouts_match_the_physical_tile_scans() {
    let expected: HashMap<(u8, String), [Option<String>; 3]> = [
        ((11, "A"), [Some("Asteroid"), None, Some("ProtoPlanet")]),
        ((11, "B"), [Some("Asteroid"), None, None]),
        ((12, "A"), [Some("ProtoPlanet"), None, Some("Transdim")]),
        ((12, "B"), [None, None, Some("Asteroid")]),
        ((13, "A"), [None, Some("Asteroid"), Some("Transdim")]),
        ((13, "B"), [None, Some("Asteroid"), None]),
        ((14, "A"), [None, Some("Asteroid"), Some("ProtoPlanet")]),
        ((14, "B"), [None, Some("Asteroid"), None]),
        ((15, "A"), [None, None, Some("ProtoPlanet")]),
        ((15, "B"), [None, Some("Asteroid"), Some("ProtoPlanet")]),
        ((16, "A"), [None, Some("ProtoPlanet"), None]),
        ((16, "B"), [None, Some("Asteroid"), Some("Asteroid")]),
        ((17, "A"), [None, None, Some("Transdim")]),
        ((17, "B"), [Some("Asteroid"), None, None]),
        ((18, "A"), [None, None, Some("ProtoPlanet")]),
        ((18, "B"), [Some("Asteroid"), None, None]),
    ]
    .into_iter()
    .map(|((id, side), planets)| {
        (
            (id, side.to_string()),
            planets.map(|planet| planet.map(str::to_string)),
        )
    })
    .collect();

    let actual: HashMap<(u8, String), [Option<String>; 3]> = load_sectors()
        .sectors
        .into_iter()
        .filter(|sector| (11..=18).contains(&sector.id))
        .map(|sector| {
            let side = sector.side.unwrap_or_default();
            let planets = std::array::from_fn(|index| sector.hexes[index].planet.clone());
            ((sector.id, side), planets)
        })
        .collect();

    assert_eq!(actual, expected);
}
