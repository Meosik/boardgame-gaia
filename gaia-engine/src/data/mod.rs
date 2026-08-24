pub mod factions;
pub mod research_tracks;
pub mod sectors;

pub use factions::{load_factions, FactionData, FactionDataFile};
pub use research_tracks::{get_level_effect, load_research_tracks, LevelEffect};
pub use sectors::{category_for_sector, load_sectors, SectorCategory, SectorTemplate};

// ── Tests ─────────────────────────────────────────────────────────────────────
//
// These guard against invalid TOML syntax in the embedded data files
// (data/sectors.toml, data/factions.toml, data/research_tracks.toml).
// `load_*()` panics via `.expect()` on a parse failure, and that panic is
// only ever reached lazily at runtime (e.g. the first "Build a Mine" action
// touches `load_factions()`), so a syntax typo in these files can silently
// pass `cargo build` and only surface as a mid-game server panic. Calling
// each loader here turns that into an immediate `cargo test` failure.

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sectors_toml_parses() {
        let file = load_sectors();
        assert!(!file.sectors.is_empty(), "sectors.toml yielded no sectors");
    }

    #[test]
    fn factions_toml_parses() {
        let file = load_factions();
        assert!(
            !file.factions.is_empty(),
            "factions.toml yielded no factions"
        );
        for faction in &file.factions {
            assert!(
                !faction.starting_structures.is_empty(),
                "faction {} has no starting_structures",
                faction.id
            );
        }
    }

    #[test]
    fn research_tracks_toml_parses() {
        let file = load_research_tracks();
        assert!(
            !file.tracks.is_empty(),
            "research_tracks.toml yielded no tracks"
        );
        for track in &file.tracks {
            assert!(!track.levels.is_empty(), "track {} has no levels", track.id);
        }
    }
}
