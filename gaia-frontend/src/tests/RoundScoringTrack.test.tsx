import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { roundScoringTileImageSrc } from '../assets/roundScoringTileImages';
import { RoundScoringTrack } from '../components/RoundScoringTrack';
import type { RoundTile } from '../types/game';

const tiles: RoundTile[] = [
  { id: 1, condition: 'BuildMine', vp_per_unit: 2 },
  { id: 2, condition: 'TerraformingStep', vp_per_unit: 2 },
  { id: 3, condition: 'BuildMineOnGaia', vp_per_unit: 4 },
  { id: 4, condition: 'UpgradeTradingStation', vp_per_unit: 3 },
  { id: 5, condition: 'FormFederation', vp_per_unit: 5 },
  { id: 12, condition: 'UpgradeResearchLab', vp_per_unit: 4 },
];

describe('RoundScoringTrack', () => {
  it('maps every supported id to exactly one matching image asset', () => {
    for (let id = 1; id <= 12; id += 1) {
      const imageSrc = roundScoringTileImageSrc(id);
      expect(imageSrc).toBeDefined();
      expect(imageSrc).not.toMatch(/round_scoring_\d+_score_.*\.jpg$/);
    }
    expect(roundScoringTileImageSrc(1)).toBe('/assets/gaiaproject/round_mine2.png');
    expect(roundScoringTileImageSrc(12)).toContain('round_scoring_12_tile.webp');
    expect(roundScoringTileImageSrc(0)).toBeUndefined();
    expect(roundScoringTileImageSrc(13)).toBeUndefined();
  });

  it('renders all six tiles and highlights the active round', () => {
    render(<RoundScoringTrack tiles={tiles} currentRound={2} />);

    expect(screen.getByText('2 / 6')).toBeInTheDocument();
    expect(screen.getAllByRole('article')).toHaveLength(6);
    expect(screen.getByText('테라포밍 단계 사용')).toBeInTheDocument();
    expect(screen.getAllByText('단위당 +2 VP')).toHaveLength(2);
    expect(screen.getByRole('article', { current: 'step' })).toHaveTextContent('R2');
    expect(screen.getByAltText('라운드 2: 테라포밍 단계 사용')).toBeInTheDocument();
  });

  it('marks earlier rounds complete without hiding their rule text', () => {
    render(<RoundScoringTrack tiles={tiles} currentRound={4} />);

    const firstRound = screen.getByText('R1').closest('article');
    expect(firstRound).toHaveClass('complete');
    expect(screen.getByText('광산 건설')).toBeInTheDocument();
  });
});
