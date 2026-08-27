import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { SpaceshipBoards } from '../components/SpaceshipBoards';
import type { PlayerState, SpaceshipBoard } from '../types/game';

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

function mockShip(overrides: Partial<SpaceshipBoard> = {}): SpaceshipBoard {
  return {
    id: 'Twilight',
    explorers: [null, null, null, null],
    artifact_pool: [],
    federation_token: 8,
    ...overrides,
  };
}

describe('SpaceshipBoards', () => {
  it('renders all four ship boards', () => {
    const ships = [
      mockShip({ id: 'Twilight' }),
      mockShip({ id: 'Rebellion' }),
      mockShip({ id: 'TFMars' }),
      mockShip({ id: 'Eclipse' }),
    ];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[mockPlayer()]} />);

    expect(screen.getByRole('img', { name: 'Twilight 함선 보드' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Eclipse 함선 보드' })).toBeInTheDocument();
    expect(screen.queryAllByLabelText(/탐사 완료/)).toHaveLength(0);
  });

  it('marks occupied explorer slots', () => {
    const ships = [mockShip({ id: 'Twilight', explorers: [0, null, null, null] })];
    const players = [mockPlayer({ player_id: 0, faction: 'Xenos' })];
    render(<SpaceshipBoards spaceshipBoards={ships} players={players} />);

    expect(screen.getByLabelText('탐사 셔틀 1 슬롯 탐사 완료')).toBeInTheDocument();
    expect(screen.queryByLabelText('탐사 셔틀 2 슬롯 탐사 완료')).not.toBeInTheDocument();
  });
});
