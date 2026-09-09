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
    tech_tiles: [],
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

  it('widens Twilight shuttle spacing around its fixed third slot', () => {
    const ships = [mockShip({ id: 'Twilight', explorers: [0, 0, 0, 0] })];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[mockPlayer()]} />);

    const slots = screen.getAllByLabelText(/탐사 셔틀 .* 슬롯 탐사 완료/);
    expect(slots.map((slot) => parseFloat(slot.style.top))).toEqual([25.35, 42.13, 59.11, 76.49]);
  });

  it('uses the wider, left-shifted shuttle spacing on Rebellion only', () => {
    const ships = [mockShip({ id: 'Rebellion', explorers: [0, 0, 0, 0] })];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[mockPlayer()]} />);

    const slots = screen.getAllByLabelText(/탐사 셔틀 .* 슬롯 탐사 완료/);
    expect(slots).toHaveLength(4);
    expect(parseFloat(slots[0].style.left)).toBeCloseTo(22.75 - 75 * 100 / 2135, 4);
    expect(slots.map((slot) => parseFloat(slot.style.top))).toEqual([
      25.95 - 15 * 100 / 736,
      43.25 - 10 * 100 / 736,
      60.75 - 10 * 100 / 736,
      78.65 - 10 * 100 / 736,
    ]);
  });

  it('spreads and raises all four T F Mars shuttle slots', () => {
    const ships = [mockShip({ id: 'TFMars', explorers: [0, 0, 0, 0] })];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[mockPlayer()]} />);

    const slots = screen.getAllByLabelText(/탐사 셔틀 .* 슬롯 탐사 완료/);
    expect(slots).toHaveLength(4);
    expect(slots.map((slot) => parseFloat(slot.style.left))).toEqual(
      Array(4).fill(22.75 - 25 * 100 / 2172),
    );
    expect(slots.map((slot) => parseFloat(slot.style.top))).toEqual([
      23.14 + 10 * 100 / 724,
      40.47 + 5 * 100 / 724,
      58.01 + 5 * 100 / 724,
      75.94 - 5 * 100 / 724,
    ]);
  });

  it('moves Eclipse shuttles right and increases their spacing', () => {
    const ships = [mockShip({ id: 'Eclipse', explorers: [0, 0, 0, 0] })];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[mockPlayer()]} />);

    const slots = screen.getAllByLabelText(/탐사 셔틀 .* 슬롯 탐사 완료/);
    expect(slots.map((slot) => parseFloat(slot.style.left))).toEqual([
      22.75 + 83 * 100 / 2172,
      22.75 + 80 * 100 / 2172,
      22.75 + 80 * 100 / 2172,
      22.75 + 80 * 100 / 2172,
    ]);
    expect(slots.map((slot) => parseFloat(slot.style.top))).toEqual([
      22.586 - 10 * 100 / 724,
      40.879,
      59.392 - 5 * 100 / 724,
      78.285 - 5 * 100 / 724,
    ]);
  });

  it('renders randomized tech, artifact, and federation components in their ship slots', () => {
    const ships = [
      mockShip({ id: 'Twilight', artifact_pool: [1, 2, 3, 4], federation_token: 8 }),
      mockShip({ id: 'TFMars', tech_tiles: [11, 11, 11, 11], federation_token: 9 }),
    ];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[]} />);

    expect(screen.getAllByAltText(/^아티팩트 /)).toHaveLength(4);
    expect(screen.getByAltText('T F Mars 표준 기술 타일 11')).toBeInTheDocument();
    expect(screen.getByAltText('Twilight 연방 토큰 8')).toBeInTheDocument();
    expect(screen.getByAltText('T F Mars 연방 토큰 9')).toBeInTheDocument();
    expect(screen.getByAltText('Twilight 연방 토큰 8')).toHaveAttribute(
      'src',
      expect.stringContaining('federation_tokens_lost_fleet/normalized/fed_08.png'),
    );
  });

  it("positions each spaceship's tech-tile slot at its own measured socket", () => {
    const ships = [
      mockShip({ id: 'Eclipse', tech_tiles: [11] }),
      mockShip({ id: 'TFMars', tech_tiles: [11] }),
      mockShip({ id: 'Rebellion', tech_tiles: [11] }),
    ];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[]} />);

    const slots = screen.getAllByAltText(/표준 기술 타일 11/).map((tile) => tile.parentElement);

    expect(slots).toHaveLength(3);
    // Each board prints its own cockpit-screen panel at a different size/position rather than
    // sharing one physical tile ratio — all three re-measured directly off their scans (see
    // `TECH_TILE_SLOT`'s comment).
    expect(screen.getByAltText('Eclipse 표준 기술 타일 11').parentElement)
      .toHaveStyle({ width: '16.53%', aspectRatio: '359 / 300' });
    expect(screen.getByAltText('T F Mars 표준 기술 타일 11').parentElement)
      .toHaveStyle({ width: '16.55%', aspectRatio: '359.5 / 285' });
    expect(screen.getByAltText('Rebellion 표준 기술 타일 11').parentElement)
      .toHaveStyle({ width: '17.03%', aspectRatio: '363.5 / 316' });
    expect(slots.every((slot) => slot?.style.height === '')).toBe(true);
  });

  it('moves only the two upper Twilight artifacts down by their measured pixel offsets', () => {
    const ships = [
      mockShip({ id: 'Twilight', artifact_pool: [1, 2, 3, 4], federation_token: 8 }),
    ];
    render(<SpaceshipBoards spaceshipBoards={ships} players={[]} />);

    expect(parseFloat(screen.getByAltText('아티팩트 1').style.top))
      .toBeCloseTo(27 + 100 / 724, 4);
    expect(parseFloat(screen.getByAltText('아티팩트 2').style.top))
      .toBeCloseTo(28 + 200 / 724, 4);
    expect(screen.getByAltText('아티팩트 3')).toHaveStyle({ top: '67.5%' });
    expect(screen.getByAltText('아티팩트 4')).toHaveStyle({ top: '68%' });
  });
});
