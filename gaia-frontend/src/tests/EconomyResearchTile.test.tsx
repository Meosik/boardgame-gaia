import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ResearchBoard } from '../components/PlayerDashboard/ResearchBoard';
import type { EconomyResearchTileSide, ResearchBoard as ResearchBoardState } from '../types/game';

function board(side: EconomyResearchTileSide): ResearchBoardState {
  return {
    tracks: {
      Terraforming: { player_levels: {}, alliance_taken: [] },
      Navigation: { player_levels: {}, alliance_taken: [] },
      ArtificialIntelligence: { player_levels: {}, alliance_taken: [] },
      GaiaProject: { player_levels: {}, alliance_taken: [] },
      Economy: { player_levels: {}, alliance_taken: [] },
      Science: { player_levels: {}, alliance_taken: [] },
    },
    tech_tiles: [],
    advanced_tech_tiles: [null, null, null, null, null, null],
    federation_tokens: [],
    economy_research_tile_side: side,
  };
}

describe('Economy level 3·4 replacement tile', () => {
  it.each([
    ['Power', '파워 면'],
    ['VictoryPoints', '승점 면'],
  ] as const)('renders the randomized %s side over the research board', (side, label) => {
    render(<ResearchBoard players={[]} board={board(side)} />);

    const overlay = screen.getByAltText(`경제 연구 3·4레벨 대체 타일 — ${label}`);
    expect(overlay).toHaveClass('research-board-economy-overlay');
    expect(overlay).toHaveAttribute(
      'src',
      expect.stringContaining(side === 'Power' ? 'economy_research_power' : 'economy_research_victory_points'),
    );
  });
});
