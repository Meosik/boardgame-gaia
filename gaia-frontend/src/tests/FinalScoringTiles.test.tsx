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
      expect(imageSrc).toContain(`final_${String(id).padStart(2, '0')}.webp`);
    }
    expect(finalScoringTileImageSrc(4)).toContain('final_04.webp');
    expect(finalScoringTileImageSrc(7)).toBeUndefined();
  });

  it('renders the selected two tiles with their rank awards', () => {
    render(<FinalScoringTiles tiles={tiles} />);

    expect(screen.getAllByRole('article')).toHaveLength(2);
    expect(screen.getByAltText('개척한 소행성 수')).toBeInTheDocument();
    expect(screen.getByAltText('배치한 위성 수')).toBeInTheDocument();
    expect(screen.getAllByText('승점: 1위 18점 · 2위 12점 · 3위 6점')).toHaveLength(2);
  });
});
