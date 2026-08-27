import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { finalScoringTileImageSrc } from '../assets/finalScoringTileImages';
import { FinalScoringTiles } from '../components/FinalScoringTiles';
import type { FinalScoringTile } from '../types/game';

const tiles: FinalScoringTile[] = [
  {
    id: 6,
    condition: 'MostAsteroids',
    vp_1st: 18,
    vp_2nd: 12,
    vp_3rd: 6,
  },
  {
    id: 10,
    condition: 'MostSatellites',
    vp_1st: 18,
    vp_2nd: 12,
    vp_3rd: 6,
  },
];

describe('FinalScoringTiles', () => {
  it('maps all nine physical asset ids and rejects the missing id 7', () => {
    for (const id of [1, 2, 3, 4, 5, 6, 8, 9, 10]) {
      const imageSrc = finalScoringTileImageSrc(id);
      expect(imageSrc).toBeDefined();
      expect(imageSrc).not.toMatch(/final_scoring_\d+_most_.*\.jpg$/);
    }
    expect(finalScoringTileImageSrc(1)).toBe('/assets/gaiaproject/final_gaia.png');
    expect(finalScoringTileImageSrc(6)).toContain('final_scoring_06_tile.webp');
    expect(finalScoringTileImageSrc(7)).toBeUndefined();
  });

  it('renders the selected two tiles with their rank awards', () => {
    render(<FinalScoringTiles tiles={tiles} />);

    expect(screen.getAllByRole('article')).toHaveLength(2);
    expect(screen.getByAltText('개척한 소행성 수')).toBeInTheDocument();
    expect(screen.getByAltText('배치한 위성 수')).toBeInTheDocument();
    expect(screen.getAllByText('1위 18 · 2위 12 · 3위 6 VP')).toHaveLength(2);
  });
});
