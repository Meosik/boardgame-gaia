import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FederationTokens } from '../components/FederationTokens';
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

describe('FederationTokens', () => {
  it('renders nothing when the supply is empty and nobody holds a token', () => {
    const { container } = render(<FederationTokens availableTokens={[]} players={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('groups the remaining supply into per-kind stacks with a count badge', () => {
    render(<FederationTokens availableTokens={[1, 1, 3, 5, 5, 5]} players={[]} />);

    expect(screen.getByLabelText('연방 토큰 1 보급 2개')).toBeInTheDocument();
    expect(screen.getByLabelText('연방 토큰 3 보급 1개')).toBeInTheDocument();
    expect(screen.getByLabelText('연방 토큰 5 보급 3개')).toBeInTheDocument();
    expect(screen.getAllByAltText(/^연방 토큰 \d+$/)).toHaveLength(3);
  });

  it('uses the normalized upscaled art and omits the Gleens-only reward from shared supply', () => {
    render(<FederationTokens availableTokens={[1, 7]} players={[]} />);

    expect(screen.getByAltText('연방 토큰 1')).toHaveAttribute(
      'src',
      expect.stringContaining('federation_tokens/normalized/fed_01.webp'),
    );
    expect(screen.queryByLabelText(/연방 토큰 7 보급/)).not.toBeInTheDocument();
  });

  it('uses cropped and orientation-corrected Lost Fleet federation art', () => {
    render(<FederationTokens availableTokens={[]} players={[
      mockPlayer({ nickname: 'Alice', federation_tokens: [8] }),
    ]} />);

    expect(screen.getByAltText('Alice 보유 연방 토큰 8')).toHaveAttribute(
      'src',
      expect.stringContaining('federation_tokens_lost_fleet/normalized/fed_08.png'),
    );
  });

  it("renders a player's green (spendable) and gray (flipped) holdings", () => {
    const players = [
      mockPlayer({
        player_id: 0,
        nickname: 'Alice',
        federation_tokens: [2, 4],
        gray_federation_tokens: [6],
      }),
    ];
    render(<FederationTokens availableTokens={[]} players={players} />);

    expect(screen.getByAltText('Alice 보유 연방 토큰 2')).toBeInTheDocument();
    expect(screen.getByAltText('Alice 보유 연방 토큰 4')).toBeInTheDocument();
    const flipped = screen.getByAltText('Alice 사용(회색면) 연방 토큰 6');
    expect(flipped).toBeInTheDocument();
    expect(flipped).toHaveClass('federation-token-mini--flipped');
    expect(flipped).toHaveAttribute(
      'src',
      expect.stringContaining('federation_tokens/normalized/back/runtime/fed_06.webp'),
    );
  });

  it('reuses token 1 front art because both physical faces are identical', () => {
    render(<FederationTokens availableTokens={[]} players={[
      mockPlayer({ nickname: 'Alice', gray_federation_tokens: [1] }),
    ]} />);

    expect(screen.getByAltText('Alice 사용(회색면) 연방 토큰 1')).toHaveAttribute(
      'src',
      expect.stringContaining('federation_tokens/normalized/fed_01.webp'),
    );
  });

  it('omits a player with no federation tokens at all from the holdings list', () => {
    const players = [
      mockPlayer({ player_id: 0, nickname: 'Alice', federation_tokens: [1] }),
      mockPlayer({ player_id: 1, nickname: 'Bob', federation_tokens: [] }),
    ];
    render(<FederationTokens availableTokens={[]} players={players} />);

    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.queryByText('Bob')).not.toBeInTheDocument();
  });
});
