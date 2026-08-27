import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GameOverScreen } from '../components/GameOverScreen';
import type { FinalResult } from '../store/gameStore';
import type { PlayerState } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: 'P0',
    faction: 'Terrans',
    resources: {
      ore: 0,
      credits: 0,
      knowledge: 0,
      qic: 0,
      power: { bowl1: 0, bowl2: 0, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 0,
    setup_bid_vp: 0,
    passed: true,
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

const players: PlayerState[] = [
  mockPlayer({ player_id: 0, nickname: 'Alice', faction: 'Terrans' }),
  mockPlayer({ player_id: 1, nickname: 'Bob', faction: 'Xenos' }),
  mockPlayer({ player_id: 2, nickname: 'Carol', faction: 'Ambas' }),
  mockPlayer({ player_id: 3, nickname: 'Dave', faction: 'Itars' }),
];

const result: FinalResult = {
  finalScores: [
    [0, 42],
    [1, 58],
    [2, 30],
    [3, 51],
  ],
  winner: 1,
};

describe('GameOverScreen', () => {
  it('ranks players by score, highest first', () => {
    render(
      <GameOverScreen result={result} players={players} myPlayerId={0} onReturnToLobby={() => {}} />
    );

    const names = Array.from(document.querySelectorAll('.game-over-name')).map(
      (el) => el.textContent?.replace('👑', '').trim()
    );
    expect(names).toEqual(['Bob', 'Dave', 'Alice', 'Carol']);
  });

  it('marks the declared winner and shows every final score', () => {
    render(
      <GameOverScreen result={result} players={players} myPlayerId={0} onReturnToLobby={() => {}} />
    );

    expect(screen.getByText('Bob').closest('li')).toHaveClass('game-over-row--winner');
    expect(screen.getByText('58 VP')).toBeInTheDocument();
    expect(screen.getByText('42 VP')).toBeInTheDocument();
  });

  it('invokes the return-to-lobby callback', () => {
    const onReturnToLobby = vi.fn();
    render(
      <GameOverScreen result={result} players={players} myPlayerId={0} onReturnToLobby={onReturnToLobby} />
    );

    fireEvent.click(screen.getByRole('button', { name: '로비로 돌아가기' }));
    expect(onReturnToLobby).toHaveBeenCalledOnce();
  });
});
