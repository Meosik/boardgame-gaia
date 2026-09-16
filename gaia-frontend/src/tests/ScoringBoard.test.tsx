import { roundScoringTileBackImageSrc } from '../assets/roundScoringTileImages';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ScoringBoard } from '../components/ScoringBoard';
import type { FinalScoringTile, GameState, RoundTile } from '../types/game';
import { decodeHexCoordinates } from '../api/websocket';
import { structureImageSrc } from '../assets/structureImages';
import progressFixture from './fixtures/finalScoringProgress.json';

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

    const completed = screen.getByLabelText('라운드 1 점수 타일 (완료됨)');
    expect(completed).toHaveClass('scoring-board-tile--flipped');
    expect(completed.querySelector('.scoring-board-tile-back'))
      .toHaveAttribute('src', roundScoringTileBackImageSrc);
    expect(screen.getByLabelText('라운드 4 점수 타일')).not.toHaveClass('scoring-board-tile--flipped');
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
    expect(screen.queryByLabelText('게임 종료 목표 달성량')).not.toBeInTheDocument();
  });

  it('shows both goals for all players, faction pieces and actual overflow numbers', () => {
    const gameState = decodeHexCoordinates(structuredClone(progressFixture.state)) as GameState;
    const tiles: FinalScoringTile[] = [
      { id: 5, condition: 'MostBuildings', vp_1st: 18, vp_2nd: 12, vp_3rd: 6 },
      { id: 9, condition: 'GreatestDistancePiAcademy', vp_1st: 18, vp_2nd: 12, vp_3rd: 6 },
    ];
    const { container } = render(<ScoringBoard roundTiles={roundTiles} finalScoringTiles={tiles}
      currentRound={4} gameState={gameState} />);
    const markers = container.querySelectorAll('[data-goal-index]');
    expect(markers).toHaveLength(8);
    const overflow = container.querySelector('[data-goal-index="0"][data-player="3"]')!;
    expect(overflow).toHaveAttribute('data-column', '10');
    expect(overflow).toHaveAttribute('data-value', '13');
    expect(overflow.querySelector('text')).toHaveTextContent('13');
    expect(overflow.querySelector('image')).toHaveAttribute('href', structureImageSrc('yellow', 'marker'));
    expect(container.querySelector('[data-goal-index="1"][data-player="3"] text')).toHaveTextContent('12');
    expect(container.querySelector('[data-player="0"] image')).toHaveAttribute('href', structureImageSrc('blue', 'marker'));
  });

  it('stacks equal/clamped values vertically and follows snapshot replacement in either direction', () => {
    const gameState = decodeHexCoordinates(structuredClone(progressFixture.state)) as GameState;
    const tiles: FinalScoringTile[] = finalScoringTiles.map(tile => ({ ...tile, condition: 'MostBuildings' }));
    for (const player of gameState.players) player.artifact_mines = Array(12).fill('Asteroid');
    const { container, rerender } = render(<ScoringBoard roundTiles={roundTiles} finalScoringTiles={tiles}
      currentRound={4} gameState={gameState} />);
    const marks = [...container.querySelectorAll('[data-goal-index="0"]')];
    expect(marks.every(m => m.getAttribute('data-column') === '10')).toBe(true);
    expect(new Set(marks.map(m => m.getAttribute('transform'))).size).toBe(4);
    const oldTransforms = marks.map(m => m.getAttribute('transform'));
    const earlier = structuredClone(gameState);
    earlier.board.hexes = {};
    earlier.board.lost_planet = null;
    earlier.players.forEach(p => { p.structures = []; p.artifact_mines = []; });
    rerender(<ScoringBoard roundTiles={roundTiles} finalScoringTiles={tiles} currentRound={0} gameState={earlier} />);
    expect([...container.querySelectorAll('[data-goal-index]')].every(m => m.getAttribute('data-value') === '0')).toBe(true);
    expect(container.querySelectorAll('.scoring-board-goal-overflow')).toHaveLength(0);
    rerender(<ScoringBoard roundTiles={roundTiles} finalScoringTiles={tiles} currentRound={4} gameState={gameState} />);
    expect([...container.querySelectorAll('[data-goal-index="0"]')].map(m => m.getAttribute('transform'))).toEqual(oldTransforms);
  });
});
