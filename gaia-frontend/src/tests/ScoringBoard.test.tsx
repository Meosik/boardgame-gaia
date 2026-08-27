import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoringBoard } from '../components/ScoringBoard';
import type { FinalScoringTile, RoundTile } from '../types/game';

const roundTiles: RoundTile[] = [
  { id: 1, condition: 'BuildMine', vp_per_unit: 2 },
  { id: 2, condition: 'TerraformingStep', vp_per_unit: 2 },
  { id: 3, condition: 'BuildMineOnGaia', vp_per_unit: 4 },
  { id: 4, condition: 'UpgradeTradingStation', vp_per_unit: 3 },
  { id: 5, condition: 'FormFederation', vp_per_unit: 5 },
  { id: 12, condition: 'UpgradeResearchLab', vp_per_unit: 4 },
];

const finalScoringTiles: FinalScoringTile[] = [
  { id: 6, condition: 'MostAsteroids', vp_1st: 18, vp_2nd: 12, vp_3rd: 6 },
  { id: 10, condition: 'MostSatellites', vp_1st: 18, vp_2nd: 12, vp_3rd: 6 },
];

describe('ScoringBoard', () => {
  it('renders the shared board image plus all 6 round tiles and both final-scoring tiles', () => {
    render(
      <ScoringBoard roundTiles={roundTiles} finalScoringTiles={finalScoringTiles} currentRound={0} />,
    );

    expect(screen.getByRole('img', { name: '점수 보드' })).toBeInTheDocument();
    for (let round = 1; round <= 6; round += 1) {
      expect(screen.getByLabelText(`라운드 ${round} 점수 타일`)).toBeInTheDocument();
    }
    expect(screen.getByAltText('게임 종료 점수 타일 1')).toBeInTheDocument();
    expect(screen.getByAltText('게임 종료 점수 타일 2')).toBeInTheDocument();
  });

  it('flips only the tiles for rounds strictly before the current round', () => {
    render(
      <ScoringBoard roundTiles={roundTiles} finalScoringTiles={finalScoringTiles} currentRound={4} />,
    );

    expect(screen.getByLabelText('라운드 1 점수 타일 (완료됨)')).toBeInTheDocument();
    expect(screen.getByLabelText('라운드 2 점수 타일 (완료됨)')).toBeInTheDocument();
    expect(screen.getByLabelText('라운드 3 점수 타일 (완료됨)')).toBeInTheDocument();
    expect(screen.getByLabelText('라운드 4 점수 타일')).toBeInTheDocument();
    expect(screen.getByLabelText('라운드 5 점수 타일')).toBeInTheDocument();
    expect(screen.getByLabelText('라운드 6 점수 타일')).toBeInTheDocument();
  });

  it('flips nothing when currentRound is 0 (pre-game preview)', () => {
    render(
      <ScoringBoard roundTiles={roundTiles} finalScoringTiles={finalScoringTiles} currentRound={0} />,
    );

    expect(screen.queryByLabelText(/완료됨/)).not.toBeInTheDocument();
  });
});
