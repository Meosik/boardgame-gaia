import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { OpponentPanels } from '../components/OpponentPanels';
import type { PlayerState } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 1,
    nickname: 'P1',
    faction: 'Xenos',
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

describe('OpponentPanels', () => {
  it('renders compact resource rows with expandable faction boards', () => {
    const players = [
      mockPlayer({ player_id: 1, nickname: 'P1', faction: 'Xenos' }),
      mockPlayer({ player_id: 2, nickname: 'P2', faction: 'Ivits' }),
    ];
    render(<OpponentPanels players={players} />);

    expect(screen.getByText('P1')).toBeInTheDocument();
    expect(screen.getByText('P2')).toBeInTheDocument();
    expect(screen.getAllByText('O 4')).toHaveLength(2);
    expect(screen.getByRole('img', { name: 'Xenos 종족 보드' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Ivits 종족 보드' })).toBeInTheDocument();
  });

  it('renders nothing when there are no opponents', () => {
    const { container } = render(<OpponentPanels players={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
