use serde::Deserialize;

static RESEARCH_TRACKS_TOML: &str = include_str!("../../data/research_tracks.toml");

#[derive(Debug, Deserialize)]
pub struct ResearchTrackFile {
    pub tracks: Vec<TrackData>,
}

#[derive(Debug, Deserialize)]
pub struct TrackData {
    pub id: String,
    pub levels: Vec<LevelEffect>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct LevelEffect {
    pub level: u8,
    pub ore: i8,
    pub credits: i8,
    pub knowledge: i8,
    pub qic: i8,
    pub vp: i8,
    #[serde(default)]
    pub gaiaformers: u8,
    #[serde(default)]
    pub power_charge: u8,
    #[serde(default)]
    pub federation_token: bool,
    #[serde(default)]
    pub lost_planet_access: bool,
}

pub fn load_research_tracks() -> ResearchTrackFile {
    #[allow(clippy::expect_used)]
    toml::from_str(RESEARCH_TRACKS_TOML)
        .expect("research_tracks.toml embedded at compile time — parse failure is a build error")
}

pub fn get_level_effect(track_id: &str, level: u8) -> Option<LevelEffect> {
    let file = load_research_tracks();
    file.tracks
        .into_iter()
        .find(|t| t.id == track_id)
        .and_then(|t| t.levels.into_iter().find(|l| l.level == level))
}
