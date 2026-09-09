import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import {
  PlanetActionPopup,
  rangeRequirementNotice,
  terraformingStepsFor,
} from '../components/PlanetActionPopup';
import type { Hex, PlanetType, PlayerState } from '../types/game';

function player(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    faction: 'Terrans',
    resources: {
      ore: 10,
      credits: 10,
      knowledge: 3,
      qic: 2,
      power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [{ hex: { q: 0, r: 0 }, kind: 'Mine' }],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 1, economy: 0, science: 0 },
    gaiaformers_total: 1,
    gaiaformers_deployed: 0,
    ...overrides,
  } as PlayerState;
}

function planetHex(planetType: PlanetType = 'Desert'): Hex {
  return {
    coord: { q: 1, r: 2 },
    planet: { planet_type: planetType, is_gaia_formed: false, owner: null },
    structures: [],
    satellites: [],
    space_tile_kind: null,
  };
}

const board = {
  sectors: [],
  hexes: Object.fromEntries([0, 1, 2].map((q) => [`${q},0`, {
    coord: { q, r: 0 },
    planet: q === 2 ? planetHex().planet : null,
    structures: q === 0 ? [{ owner: 0, kind: 'Mine' as const }] : [],
    satellites: [],
    space_tile_kind: null,
  }])),
  lost_planet: null,
  spaceship_tiles: {},
};

describe('PlanetActionPopup', () => {
  it('uses direct planet action selection and separates terraforming steps from mine cost', () => {
    const onConfirm = vi.fn();
    const onSuppressTerraformOreConfirmation = vi.fn();
    const me = player();
    render(
      <PlanetActionPopup
        anchor={{ x: 100, y: 100 }}
        hex={planetHex()}
        player={me}
        players={[me]}
        board={{
          ...board,
          hexes: {
            ...board.hexes,
            '1,2': planetHex(),
            '0,1': { ...planetHex(), coord: { q: 0, r: 1 }, planet: null },
            '1,1': { ...planetHex(), coord: { q: 1, r: 1 }, planet: null },
          },
        }}
        onSuppressTerraformOreConfirmation={onSuppressTerraformOreConfirmation}
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByLabelText(
      '필요 자원: 광석 1, 크레딧 2, 정보 큐브 1',
    )).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '광산 건설' }));
    expect(screen.getByLabelText(
      '광산 건설비: 광석 1, 크레딧 2, 정보 큐브 1',
    )).toBeInTheDocument();
    expect(screen.getByLabelText('테라포밍 2단계')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '행동 확정' }));
    expect(screen.getByText('테라포밍 광석 사용 확인')).toBeInTheDocument();
    expect(screen.getByText('테라포밍 2단계에 광석 6개를 추가로 사용합니다.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('checkbox', { name: '이 게임 동안 다시 보지 않기' }));
    fireEvent.click(screen.getByRole('button', { name: '광석 6개 사용 확인' }));
    expect(onConfirm).toHaveBeenCalledWith({ type: 'Build', coord: { q: 1, r: 2 } });
    expect(onSuppressTerraformOreConfirmation).toHaveBeenCalledOnce();
  });

  it('skips the extra terraforming-ore warning after it was disabled for the game', () => {
    const onConfirm = vi.fn();
    const me = player();
    render(
      <PlanetActionPopup
        anchor={{ x: 100, y: 100 }}
        hex={planetHex()}
        player={me}
        players={[me]}
        board={{
          ...board,
          hexes: {
            ...board.hexes,
            '1,2': planetHex(),
            '0,1': { ...planetHex(), coord: { q: 0, r: 1 }, planet: null },
            '1,1': { ...planetHex(), coord: { q: 1, r: 1 }, planet: null },
          },
        }}
        suppressTerraformOreConfirmation
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '광산 건설' }));
    fireEvent.click(screen.getByRole('button', { name: '행동 확정' }));
    expect(screen.queryByText('테라포밍 광석 사용 확인')).not.toBeInTheDocument();
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('shows the cost but blocks confirmation when the mine cannot be afforded', () => {
    const onConfirm = vi.fn();
    const me = player({
      resources: {
        ...player().resources,
        ore: 0,
      },
    });
    render(
      <PlanetActionPopup
        anchor={{ x: 100, y: 100 }}
        hex={{ ...planetHex('Terra'), coord: { q: 1, r: 0 } }}
        player={me}
        players={[me]}
        board={board}
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '광산 건설' }));
    const confirm = screen.getByRole('button', { name: '필요 자원 부족' });
    expect(confirm).toBeDisabled();
    fireEvent.click(confirm);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it('consumes an activated power action only when it provides terraforming steps', () => {
    const onConfirm = vi.fn();
    const me = player();
    render(
      <PlanetActionPopup
        anchor={{ x: 100, y: 100 }}
        hex={planetHex('Desert')}
        player={me}
        players={[me]}
        board={{
          ...board,
          hexes: {
            ...board.hexes,
            '1,2': planetHex('Desert'),
            '0,1': { ...planetHex(), coord: { q: 0, r: 1 }, planet: null },
            '1,1': { ...planetHex(), coord: { q: 1, r: 1 }, planet: null },
          },
        }}
        powerAction={{ id: 2, freeTerraformingSteps: 2 }}
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    );

    expect(screen.getByText('무료 테라포밍 2')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '광산 건설' }));
    expect(screen.queryByLabelText(/테라포밍 .*단계/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '행동 확정' }));

    expect(onConfirm).toHaveBeenCalledWith({
      type: 'PowerAction',
      id: 2,
      coord: { q: 1, r: 2 },
    });
  });

  it('automatically falls back to a normal build when no terraforming is used', () => {
    const onConfirm = vi.fn();
    const me = player();
    render(
      <PlanetActionPopup
        anchor={{ x: 100, y: 100 }}
        hex={{ ...planetHex('Terra'), coord: { q: 1, r: 0 } }}
        player={me}
        players={[me]}
        board={board}
        powerAction={{ id: 6, freeTerraformingSteps: 1 }}
        onConfirm={onConfirm}
        onClose={vi.fn()}
      />,
    );

    expect(screen.queryByText(/무료 테라포밍/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '광산 건설' }));
    fireEvent.click(screen.getByRole('button', { name: '행동 확정' }));

    expect(onConfirm).toHaveBeenCalledWith({ type: 'Build', coord: { q: 1, r: 0 } });
  });

  it('mirrors faction-specific standard-planet terraforming distances', () => {
    expect(terraformingStepsFor('Ice', player({ faction: 'Darkanians' }), [])).toBe(1);
    expect(terraformingStepsFor('Ice', player({ faction: 'SpaceGiants' }), [])).toBe(2);
    expect(terraformingStepsFor('Desert', player({ faction: 'Terrans' }), [])).toBe(2);
  });

  it('requires enough explicitly selected information cubes for the needed range', () => {
    expect(rangeRequirementNotice(0, 0)).toBeNull();
    expect(rangeRequirementNotice(1, 0)).toContain('사거리가 부족합니다');
    expect(rangeRequirementNotice(1, 1)).toBeNull();
    expect(rangeRequirementNotice(2, 1)).toContain('정보 큐브를 1개 더 추가하세요');
    expect(rangeRequirementNotice(2, 2)).toBeNull();
  });
});
