use serde::Deserialize;

static SECTORS_TOML: &str = include_str!("../../data/sectors.toml");

#[derive(Debug, Deserialize)]
pub struct SectorFile {
    pub sectors: Vec<SectorTemplate>,
}

/// Sector category — standard 19-hex tiles (01-10) or
/// 3-hex Deep Space tiles (11-18, Lost Fleet expansion).
#[derive(Debug, Deserialize, PartialEq, Default)]
#[serde(rename_all = "snake_case")]
pub enum SectorCategory {
    #[default]
    Standard,
    DeepSpace,
}

#[derive(Debug, Deserialize)]
pub struct SectorTemplate {
    pub id: u8,
    #[serde(default)]
    pub is_lost_fleet: bool,
    /// "A" or "B" for double-sided sectors (s05-s07 and all deep space tiles).
    #[serde(default)]
    pub side: Option<String>,
    #[serde(default)]
    pub category: SectorCategory,
    pub hexes: Vec<HexTemplate>,
}

#[derive(Debug, Deserialize)]
pub struct HexTemplate {
    pub rel_q: i32,
    pub rel_r: i32,
    #[serde(default)]
    pub planet: Option<String>,
}

pub fn load_sectors() -> SectorFile {
    #[allow(clippy::expect_used)]
    toml::from_str(SECTORS_TOML)
        .expect("sectors.toml embedded at compile time — parse failure is a build error")
}

/// The template category for a sector id (1-10 standard, 11-18 Deep Space).
/// Falls back to `SectorCategory::Standard` for an unknown id.
pub fn category_for_sector(id: u8) -> SectorCategory {
    load_sectors()
        .sectors
        .into_iter()
        .find(|s| s.id == id)
        .map(|s| s.category)
        .unwrap_or_default()
}
