import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResearchBoard } from '../components/PlayerDashboard/ResearchBoard';
import type { PlayerState } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: 'P0',
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 1,
      power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    gaiaformers_in_gaia_area: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
    ...overrides,
  };
}

describe('ResearchBoard', () => {
  it('renders the shared board image and one token per player per track', () => {
    const players = [
      mockPlayer({ player_id: 0, nickname: 'P0', faction: 'Terrans' }),
      mockPlayer({
        player_id: 1,
        nickname: 'P1',
        faction: 'Xenos',
        research_tracks: { terraforming: 3, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 5 },
      }),
    ];
    render(<ResearchBoard players={players} />);

    expect(screen.getByRole('img', { name: '연구판' })).toBeInTheDocument();
    // 6 tracks x 2 players = 12 tokens
    expect(screen.getAllByLabelText(/레벨/)).toHaveLength(12);
    expect(screen.getByLabelText('P1 terraforming 레벨 3')).toBeInTheDocument();
    expect(screen.getByLabelText('P1 science 레벨 5')).toBeInTheDocument();
  });

  it('skips players who have not picked a faction yet', () => {
    const players = [
      mockPlayer({ player_id: 0, faction: 'Terrans' }),
      mockPlayer({ player_id: 1, faction: null }),
    ];
    render(<ResearchBoard players={players} />);

    expect(screen.getAllByLabelText(/레벨/)).toHaveLength(6);
  });

  it('clamps out-of-range levels into the drawn track', () => {
    const players = [
      mockPlayer({
        research_tracks: { terraforming: 9, navigation: -2, ai: 0, gaia: 0, economy: 0, science: 0 },
      }),
    ];
    render(<ResearchBoard players={players} />);

    expect(screen.getByLabelText('P0 terraforming 레벨 5')).toBeInTheDocument();
    expect(screen.getByLabelText('P0 navigation 레벨 0')).toBeInTheDocument();
  });
});
