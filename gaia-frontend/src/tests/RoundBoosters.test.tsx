import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { RoundBoosters } from '../components/RoundBoosters';
import { roundBoosterImageSrc } from '../assets/roundBoosterImages';
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

describe('RoundBoosters', () => {
  it('uses clean tile assets instead of board-context JPG crops', () => {
    for (let id = 1; id <= 14; id += 1) {
      const imageSrc = roundBoosterImageSrc(id);
      expect(imageSrc).toBeDefined();
      expect(imageSrc).not.toMatch(/booster_\d+_.*\.jpg$/);
    }
    expect(roundBoosterImageSrc(1)).toBe('/assets/gaiaproject/booster_rl.png');
    expect(roundBoosterImageSrc(14)).toContain('booster_14_tile.webp');
  });

  it('renders every booster in the available pool as a real tile image', () => {
    render(<RoundBoosters availableBoosters={[1, 2, 3]} players={[]} />);

    expect(screen.getByAltText('라운드 부스터 1')).toBeInTheDocument();
    expect(screen.getByAltText('라운드 부스터 2')).toBeInTheDocument();
    expect(screen.getByAltText('라운드 부스터 3')).toBeInTheDocument();
  });

  it('also renders boosters currently held by a player (not in the available pool) with an owner marker', () => {
    const players = [mockPlayer({ player_id: 0, nickname: 'Alice', faction: 'Xenos', booster: 9 })];
    render(<RoundBoosters availableBoosters={[1, 2]} players={players} />);

    expect(screen.getByAltText('라운드 부스터 9')).toBeInTheDocument();
    expect(screen.getByLabelText('Alice 보유 중')).toBeInTheDocument();
  });

  it('renders the corrected booster 6 crop at the standard tile width', () => {
    render(<RoundBoosters availableBoosters={[5, 6, 14]} players={[]} />);

    for (const id of [5, 14]) {
      expect(screen.getByAltText(`라운드 부스터 ${id}`).closest('figure')).toHaveClass(
        'round-booster-tile--wide',
      );
    }
    expect(screen.getByAltText('라운드 부스터 6').closest('figure')).not.toHaveClass(
      'round-booster-tile--wide',
    );
  });

  it('renders nothing when there are no boosters in play', () => {
    const { container } = render(<RoundBoosters availableBoosters={[]} players={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
