import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  SpaceshipExplorePopup,
  spaceshipExploreStatus,
} from '../components/SpaceshipExplorePopup';
import type { BoardState, Hex, PlayerState, SpaceshipBoard } from '../types/game';

function player(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: '나',
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 3,
      power: { bowl1: 2, bowl2: 4, bowl3: 4, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [{ hex: { q: 0, r: 0 }, kind: 'Mine' }],
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

function emptyHex(q: number): Hex {
  return {
    coord: { q, r: 0 },
    planet: null,
    space_tile_kind: null,
    structures: q === 0 ? [{ owner: 0, kind: 'Mine' }] : [],
    satellites: [],
  };
}

function board(shipQ = 1): BoardState {
  return {
    sectors: [],
    hexes: Object.fromEntries(
      Array.from({ length: shipQ + 1 }, (_, q) => [`${q},0`, emptyHex(q)]),
    ),
    lost_planet: null,
    spaceship_tiles: { Twilight: { q: shipQ, r: 0 } },
  };
}

function ship(overrides: Partial<SpaceshipBoard> = {}): SpaceshipBoard {
  return {
    id: 'Twilight',
    explorers: [null, null, null, null],
    artifact_pool: [1, 2, 3, 4],
    tech_tiles: [],
    federation_token: 8,
    ...overrides,
  };
}

describe('SpaceshipExplorePopup', () => {
  it('confirms a basic spaceship exploration from the map tile', () => {
    const onConfirm = vi.fn();
    render(
      <SpaceshipExplorePopup
        anchor={{ x: 100, y: 100 }}
        ship="Twilight"
        spaceshipBoard={ship()}
        board={board()}
        player={player()}
        selectedRangeQic={0}
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '함선 탐사' }));
    expect(screen.getByText('탐사선')).toBeInTheDocument();
    expect(screen.getByText('승점')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '함선 탐사 확정' }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('requires enough explicitly selected range cubes', () => {
    expect(spaceshipExploreStatus(board(3), ship(), player(), 0)).toMatchObject({
      available: false,
      rangeQic: 1,
    });
    expect(spaceshipExploreStatus(board(3), ship(), player(), 1)).toMatchObject({
      available: true,
      rangeQic: 1,
    });
  });

  it('blocks a player who already explored that spaceship', () => {
    const status = spaceshipExploreStatus(board(), ship({ explorers: [0, null, null, null] }), player(), 0);
    expect(status.available).toBe(false);
    expect(status.reason).toBe('이미 이 함선을 탐사했습니다.');
  });

  it('shows the later-slot power charge before confirmation', () => {
    render(
      <SpaceshipExplorePopup
        anchor={{ x: 100, y: 100 }}
        ship="Twilight"
        spaceshipBoard={ship({ explorers: [1, null, null, null] })}
        board={board()}
        player={player()}
        selectedRangeQic={0}
        onConfirm={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '함선 탐사' }));
    expect(screen.getByText('2번 슬롯에 배치 · 파워 2 충전')).toBeInTheDocument();
  });
});
