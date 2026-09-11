import { describe, expect, it } from 'vitest';
import { ARTIFACT_LABELS } from '../components/artifactDescriptions';
import { ADVANCED_TECH_TILE_LABELS } from '../components/advancedTechDescriptions';

describe('tile effect timing descriptions', () => {
  it('separates the two income artifacts from immediate rewards', () => {
    expect(Object.keys(ARTIFACT_LABELS)).toHaveLength(13);
    for (const [id, text] of Object.entries(ARTIFACT_LABELS)) {
      expect(text.startsWith([2, 3].includes(Number(id)) ? '수입:' : '즉시:')).toBe(true);
    }
    expect(ARTIFACT_LABELS[3]).toBe('수입: 광석 1 + 지식 1');
    expect(ARTIFACT_LABELS[2]).toContain('III구역');
  });
  it('distinguishes acquisition, recurring triggers, pass and round-limited actions', () => {
    expect(Object.keys(ADVANCED_TECH_TILE_LABELS)).toHaveLength(21);
    for (const id of [1, 2, 5, 6, 9, 10, 12, 13]) expect(ADVANCED_TECH_TILE_LABELS[id]).toMatch(/^획득 즉시:/);
    for (const id of [3, 4, 8, 16, 17]) expect(ADVANCED_TECH_TILE_LABELS[id]).toContain('때마다');
    for (const id of [7, 11, 14, 15, 19]) expect(ADVANCED_TECH_TILE_LABELS[id]).toMatch(/^패스할 때:/);
    for (const id of [20, 21, 22]) expect(ADVANCED_TECH_TILE_LABELS[id]).toMatch(/^행동 \(라운드당 1회\):/);
  });
});
