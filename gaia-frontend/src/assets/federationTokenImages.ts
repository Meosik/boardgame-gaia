import fedToken01 from './federation_tokens/fed_token_01_gain_1_ore_1_knowledge_and_2_credits.jpg';
import fedToken02 from './federation_tokens/fed_token_02_score_12_vp.jpg';
import fedToken03 from './federation_tokens/fed_token_03_score_8_vp_and_gain_1_qic.jpg';
import fedToken04 from './federation_tokens/fed_token_04_score_8_vp_and_gain_2_power_tokens_to_area_i.jpg';
import fedToken05 from './federation_tokens/fed_token_05_score_7_vp_and_gain_2_ore.jpg';
import fedToken06 from './federation_tokens/fed_token_06_score_7_vp_and_gain_6_credits.jpg';
import fedToken07 from './federation_tokens/fed_token_07_score_6_vp_and_gain_2_knowledge.jpg';
import fedLf01 from './federation_tokens_lost_fleet/fed_lf_01_score_7_vp_and_gain_2_power_tokens_to_area_iii.jpg';
import fedLf02 from './federation_tokens_lost_fleet/fed_lf_02_score_4_vp_gain_2_ore_and_gain_1_qic.jpg';
import fedLf03 from './federation_tokens_lost_fleet/fed_lf_03_score_4_vp_and_gain_4_knowledge.jpg';
import fedLf04 from './federation_tokens_lost_fleet/fed_lf_04_gain_a_tech_tile.jpg';
import fedLf05 from './federation_tokens_lost_fleet/fed_lf_05_score_12_vp.jpg';
import fedLf06 from './federation_tokens_lost_fleet/fed_lf_06_immediately_perform_a_build_a_mine_action_with_up_.jpg';
import fedLf07 from './federation_tokens_lost_fleet/fed_lf_07_score_8_vp_and_gain_8_credits.jpg';
import fedLf08 from './federation_tokens_lost_fleet/fed_lf_08_immediately_perform_a_build_a_mine_action_of_limit.jpg';

// Keyed by the actual `FederationTokenKind` catalog id (`federation_token_kind` in
// gaia-engine/src/rules/engine.rs), not by the filenames' own discovery-order numbering.
const images: Record<number, string> = {
  1: fedToken02, // Flat12Vp
  2: fedToken03, // Vp8PlusQic1
  3: fedToken04, // Vp8PlusPower2
  4: fedToken05, // Vp7PlusOre2
  5: fedToken06, // Vp7PlusCredits6
  6: fedToken07, // Vp6PlusKnowledge2
  7: fedToken01, // Ore1Knowledge1Credits2
  8: fedLf07, // LostFleetVp8PlusCredits8
  9: fedLf05, // LostFleetFlat12Vp
  10: fedLf03, // LostFleetVp4PlusKnowledge4
  11: fedLf02, // LostFleetVp4PlusOre2PlusQic1
  12: fedLf04, // LostFleetTechTileOfChoice
  13: fedLf01, // LostFleetVp7PlusPower2ToArea3
  14: fedLf06, // LostFleetFreeBuild3Steps
  15: fedLf08, // LostFleetFreeBuildUnlimitedRange
  16: fedToken01, // Gleens' unique Planetary-Institute token — same printed face as id 7
};

export function federationTokenImageSrc(tokenId: number): string | undefined {
  return images[tokenId];
}
