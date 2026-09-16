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
  it('matches expansion images to the established engine conditions, not the swapped source numbers', () => {
    const expansionTiles: RoundTile[] = [
      { id: 10, condition: 'BuildMineOnNewPlanetType', vp_per_unit: 3 },
      { id: 11, condition: 'BuildMineInNewSector', vp_per_unit: 3 },
    ];
    render(<RoundScoringTrack tiles={expansionTiles} currentRound={1} />);
    expect(decodeURI(screen.getByAltText('라운드 1: 새로운 행성 유형에 광산 건설').getAttribute('src') ?? ''))
      .toContain('새행성종류광산');
    expect(decodeURI(screen.getByAltText('라운드 2: 이전에 개척하지 않은 우주·심우주 섹터에 광산 건설').getAttribute('src') ?? ''))
      .toContain('새구역광산');
  });

  it('maps every supported id to exactly one matching image asset', () => {
    for (let id = 1; id <= 12; id += 1) {
      const imageSrc = roundScoringTileImageSrc(id);
      expect(imageSrc).toBeDefined();
      expect(imageSrc).not.toMatch(/round_scoring_\d+_score_.*\.jpg$/);
    }
    expect(roundScoringTileImageSrc(1)).toContain('/normalized/round_01_');
    expect(roundScoringTileImageSrc(12)).toContain('/normalized/round_12_');
    expect(roundScoringTileImageSrc(0)).toBeUndefined();
    expect(roundScoringTileImageSrc(13)).toBeUndefined();
  });

  it('renders all six tiles and highlights the active round', () => {
    render(<RoundScoringTrack tiles={tiles} currentRound={2} />);

    expect(screen.getByText('2 / 6')).toBeInTheDocument();
    expect(screen.getAllByRole('article')).toHaveLength(6);
    expect(screen.getByText('테라포밍 단계 사용')).toBeInTheDocument();
    expect(screen.getAllByText('단위당 승점 +2점')).toHaveLength(2);
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
