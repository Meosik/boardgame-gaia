import { beforeEach, describe, it, expect, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { HexCell } from '../components/GameBoard/HexCell';
import { GameBoard } from '../components/GameBoard';
import { axialDistance, axialToPixel, hexCorners, hexKey } from '../components/GameBoard/hex-utils';
import type { Hex, PlayerState, StructureType } from '../types/game';
import { useGameStore } from '../store/gameStore';

beforeEach(() => {
  act(() => useGameStore.getState().actions.reset());
});

describe('hex-utils', () => {
  it('axialToPixel returns correct coords for origin', () => {
    const [x, y] = axialToPixel(0, 0, 36);
    expect(x).toBe(0);
    expect(y).toBe(0);
  });

  it('axialToPixel q=1 shifts x right', () => {
    const [x1] = axialToPixel(1, 0, 36);
    const [x0] = axialToPixel(0, 0, 36);
    expect(x1).toBeGreaterThan(x0);
  });

  it('hexCorners returns 6 comma-separated coordinate pairs', () => {
    const points = hexCorners(0, 0, 36);
    const pairs = points.split(' ');
    expect(pairs).toHaveLength(6);
    pairs.forEach((p) => {
      const parts = p.split(',');
      expect(parts).toHaveLength(2);
      expect(Number(parts[0])).not.toBeNaN();
      expect(Number(parts[1])).not.toBeNaN();
    });
  });

  it('hexKey formats q,r correctly', () => {
    expect(hexKey(3, -2)).toBe('3,-2');
    expect(hexKey(0, 0)).toBe('0,0');
  });

  it('axialDistance matches engine hex distance', () => {
    expect(axialDistance({ q: 0, r: 0 }, { q: 5, r: -2 })).toBe(5);
    expect(axialDistance({ q: 3, r: -2 }, { q: 3, r: -3 })).toBe(1);
  });
});

describe('GameBoard rendering', () => {
  it('renders SVG element', () => {
    // minimal board with no hexes
    const { container } = render(
      // dynamic import to avoid zustand dependency complexity in test
      <svg data-testid="board-svg" />
    );
    expect(container.querySelector('svg')).toBeTruthy();
  });

  it('normalizes every standard-sector source into the canonical 19-hex footprint', () => {
    const board = {
      sectors: [{ id: 2, rotation: 0, origin: { q: 0, r: 0 } }],
      hexes: {},
      lost_planet: null,
      spaceship_tiles: {},
    };
    const { container } = render(<GameBoard board={board} />);
    const sectorImage = container.querySelector('image');

    expect(sectorImage?.getAttribute('preserveAspectRatio')).toBe('none');
    expect(sectorImage?.getAttribute('transform')).toBe('rotate(-240 900 700)');
  });

  it('keeps printed sector planets visible instead of drawing a duplicate icon', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Desert', is_gaia_formed: false, owner: null },
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{}}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={false}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    expect(container.querySelector('image')).toBeNull();
    expect(container.querySelector('polygon')?.getAttribute('fill')).toBe('transparent');
    expect(container.querySelector('polygon')?.getAttribute('stroke')).toBe('#314B5A');
    expect(container.querySelector('polygon')?.getAttribute('stroke-width')).toBe('2.5');
  });

  it('renders the Lost Planet with the supplied upscaled action marker', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'LostPlanet', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [],
      satellites: [0],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{ 0: 'Terrans' }}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={false}
          isStandardSectorArt={false}
          mutePrintedBackground={false}
          showPlanetOverlay
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    const image = container.querySelector('image');
    expect(image?.getAttribute('href')).toContain('lost_planet.webp');
  });

  it('subdues vivid standard-sector backgrounds without covering planets', () => {
    const emptyHex: Hex = {
      coord: { q: 0, r: 0 },
      planet: null,
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={emptyHex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{}}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={true}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    const polygon = container.querySelector('polygon');
    expect(polygon?.getAttribute('fill')).toBe('#020712');
    expect(polygon?.getAttribute('fill-opacity')).toBe('0.2');
    expect(polygon?.getAttribute('stroke')).toBe('#314B5A');
  });

  it('places a faction-colored Gaiaformer on a Transdim planet during formation', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Transdim', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{ 0: 'Terrans' }}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={false}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    expect(container.querySelector('image[aria-label="가이아포머"]')).toBeTruthy();
    expect(container.querySelector('image[aria-label="가이아포머"]')?.getAttribute('href'))
      .toContain('blue_gaiaformer');
  });

  it('renders mines ten percent larger and ten pixels lower', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [{ owner: 0, kind: 'Mine' }],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{ 0: 'Terrans' }}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={false}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    const mine = container.querySelector('image');
    expect(Number(mine?.getAttribute('width'))).toBeCloseTo(36 * 0.72 * 1.1);
    expect(Number(mine?.getAttribute('height'))).toBeCloseTo(36 * 0.72 * 1.1);
    expect(Number(mine?.getAttribute('y'))).toBeCloseTo(50 - 36 * 0.893 + 10);
  });

  it('renders a Lantids mine beside the opponent structure on a shared planet', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [
        { owner: 0, kind: 'TradingStation' },
        { owner: 1, kind: 'Mine' },
      ],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{ 0: 'Xenos', 1: 'Lantids' }}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={false}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    const main = container.querySelector('image[aria-label="구조물"]');
    const lantidsMine = container.querySelector('image[aria-label="공동 점유 구조물 1"]');
    expect(main).toBeInTheDocument();
    expect(lantidsMine).toBeInTheDocument();
    expect(main?.getAttribute('href')).toContain('yellow_trading_station');
    expect(lantidsMine?.getAttribute('href')).toContain('blue_mine');
    expect(Number(lantidsMine?.getAttribute('x'))).toBeGreaterThan(50);
  });

  it('separates and enlarges structures only when the dev-game emphasis is enabled', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [{ owner: 0, kind: 'Mine' }],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{ 0: 'Terrans' }}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={false}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          emphasizeStructure
          onClick={() => undefined}
        />
      </svg>,
    );

    expect(container.querySelector('.game-board-structure-backdrop')).toBeInTheDocument();
    expect(container.querySelector('.game-board-structure-contact-shadow')).toBeInTheDocument();
    const mine = container.querySelector('image[aria-label="구조물"]');
    expect(Number(mine?.getAttribute('width'))).toBeCloseTo(36 * 0.792 * 1.12);
    expect(Number(mine?.getAttribute('y'))).toBeCloseTo(50 - 36 * 0.893 + 10 - 36 * 0.04);
  });

  it.each([
    ['Academy', { Academy: 'Science' }, 0.946],
    ['PlanetaryInstitute', 'PlanetaryInstitute', 0.99],
  ] as [string, StructureType, number][])('limits %s emphasis to five percent', (_label, kind, baseScale) => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [{ owner: 0, kind }],
      satellites: [],
    };
    const { container } = render(
      <svg>
        <HexCell
          hex={hex}
          cx={50}
          cy={50}
          size={36}
          playerFactions={{ 0: 'Terrans' }}
          isHighlighted={false}
          isSelected={false}
          isPrintedOnSectorArt={true}
          isStandardSectorArt={true}
          mutePrintedBackground={false}
          showPlanetOverlay={false}
          hasPowerRing={false}
          isDeepSpaceOutline={false}
          emphasizeStructure
          onClick={() => undefined}
        />
      </svg>,
    );

    expect(Number(container.querySelector('image[aria-label="구조물"]')?.getAttribute('width')))
      .toBeCloseTo(36 * baseScale * 1.05);
  });

  it('outlines Interspace tiles in white when the setup highlight is enabled', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: null,
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    const board = {
      sectors: [],
      hexes: { '0,0': hex },
      lost_planet: null,
      spaceship_tiles: {},
    };
    const { container } = render(<GameBoard board={board} highlightInterspace />);
    const cell = container.querySelector('[aria-label="hex 0,0"]');

    expect(cell?.querySelector('polygon')?.getAttribute('stroke')).toBe('#ffffff');
    expect(cell?.querySelector('polygon')?.getAttribute('stroke-width')).toBe('2');
  });

  it('faintly outlines only hexes inside the current basic navigation range', () => {
    const hexes = Object.fromEntries([0, 1, 2].map((q) => [`${q},0`, {
      coord: { q, r: 0 },
      planet: null,
      space_tile_kind: null,
      structures: q === 0 ? [{ owner: 0, kind: 'Mine' as const }] : [],
      satellites: [],
    }]));
    const player = {
      player_id: 0,
      faction: 'Terrans',
      structures: [{ hex: { q: 0, r: 0 }, kind: 'Mine' }],
      research_tracks: { navigation: 0 },
    } as PlayerState;
    const { container } = render(
      <GameBoard
        board={{ sectors: [], hexes, lost_planet: null, spaceship_tiles: {} }}
        players={[player]}
        rangePlayerId={0}
      />,
    );

    expect(container.querySelector('[aria-label="hex 0,0"] .game-board-range-outline')).toBeNull();
    expect(container.querySelector('[aria-label="hex 1,0"] .game-board-range-outline'))
      .toHaveAttribute('fill', 'none');
    expect(container.querySelector('[aria-label="hex 1,0"] .game-board-range-outline'))
      .toHaveAttribute('stroke-opacity', '0.58');
    expect(container.querySelector('[aria-label="hex 2,0"] .game-board-range-outline')).toBeNull();
  });

  it('extends the faint blue range preview by two hexes for one information cube', () => {
    const hexes = Object.fromEntries([0, 1, 2, 3].map((q) => [`${q},0`, {
      coord: { q, r: 0 },
      planet: null,
      space_tile_kind: null,
      structures: q === 0 ? [{ owner: 0, kind: 'Mine' as const }] : [],
      satellites: [],
    }]));
    const player = {
      player_id: 0,
      faction: 'Terrans',
      structures: [{ hex: { q: 0, r: 0 }, kind: 'Mine' }],
      research_tracks: { navigation: 0 },
    } as PlayerState;
    const { container } = render(
      <GameBoard
        board={{ sectors: [], hexes, lost_planet: null, spaceship_tiles: {} }}
        players={[player]}
        rangePlayerId={0}
        rangePreviewBonus={2}
      />,
    );

    const extended = container.querySelector('[aria-label="hex 3,0"] .game-board-range-outline');
    expect(extended).toHaveAttribute('stroke', '#7dd3fc');
    expect(extended).toHaveAttribute('fill', 'none');
    expect(extended).not.toHaveAttribute('stroke-dasharray');
  });

  it('opens board context only from the current player structure', () => {
    const ownHex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [{ owner: 0, kind: 'Mine' }],
      satellites: [],
    };
    const opponentHex: Hex = {
      coord: { q: 1, r: 0 },
      planet: { planet_type: 'Desert', is_gaia_formed: false, owner: 1 },
      space_tile_kind: null,
      structures: [{ owner: 1, kind: 'Mine' }],
      satellites: [],
    };
    const onOwnedStructureClick = vi.fn();
    render(
      <GameBoard
        board={{
          sectors: [],
          hexes: { '0,0': ownHex, '1,0': opponentHex },
          lost_planet: null,
          spaceship_tiles: {},
        }}
        interactivePlayerId={0}
        onOwnedStructureClick={onOwnedStructureClick}
      />,
    );

    fireEvent.click(screen.getByLabelText('hex 0,0'), { clientX: 123, clientY: 234 });
    expect(onOwnedStructureClick).toHaveBeenCalledWith(ownHex, { x: 123, y: 234 });

    fireEvent.click(screen.getByLabelText('hex 1,0'));
    expect(onOwnedStructureClick).toHaveBeenCalledTimes(1);
  });

  it('targets only an owned building during the DEV receive-power test', () => {
    const ownHex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [{ owner: 0, kind: 'Mine' }],
      satellites: [],
    };
    const opponentHex: Hex = {
      coord: { q: 1, r: 0 },
      planet: { planet_type: 'Desert', is_gaia_formed: false, owner: 1 },
      space_tile_kind: null,
      structures: [{ owner: 1, kind: 'ResearchLab' }],
      satellites: [],
    };
    const onPowerChargeStructureClick = vi.fn();
    render(
      <GameBoard
        board={{
          sectors: [],
          hexes: { '0,0': ownHex, '1,0': opponentHex },
          lost_planet: null,
          spaceship_tiles: {},
        }}
        interactivePlayerId={0}
        devPowerChargeTargeting
        onPowerChargeStructureClick={onPowerChargeStructureClick}
      />,
    );

    fireEvent.click(screen.getByLabelText('hex 0,0'));
    expect(onPowerChargeStructureClick).toHaveBeenCalledWith(ownHex);

    fireEvent.click(screen.getByLabelText('hex 1,0'));
    expect(onPowerChargeStructureClick).toHaveBeenCalledTimes(1);
  });

  it('does not add an opponent building to a federation selection', () => {
    const ownHex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Terra', is_gaia_formed: false, owner: 0 },
      space_tile_kind: null,
      structures: [{ owner: 0, kind: 'Mine' }],
      satellites: [],
    };
    const opponentHex: Hex = {
      coord: { q: 1, r: 0 },
      planet: { planet_type: 'Desert', is_gaia_formed: false, owner: 1 },
      space_tile_kind: null,
      structures: [{ owner: 1, kind: 'Mine' }],
      satellites: [],
    };
    const spaceshipHex: Hex = {
      coord: { q: 2, r: 0 },
      planet: null,
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    act(() => useGameStore.getState().actions.selectAction('FormFederation'));
    render(
      <GameBoard
        board={{
          sectors: [],
          hexes: { '0,0': ownHex, '1,0': opponentHex, '2,0': spaceshipHex },
          lost_planet: null,
          spaceship_tiles: { Twilight: { q: 2, r: 0 } },
        }}
        interactivePlayerId={0}
        federationSelectableHexes={[{ q: 0, r: 0 }]}
      />,
    );

    fireEvent.click(screen.getByLabelText('hex 1,0'));
    expect(useGameStore.getState().selectedHexes).toEqual([]);

    fireEvent.click(screen.getByLabelText('hex 2,0'));
    expect(useGameStore.getState().selectedHexes).toEqual([]);

    fireEvent.click(screen.getByLabelText('hex 0,0'));
    expect(useGameStore.getState().selectedHexes).toEqual([{ q: 0, r: 0 }]);
  });

  it('does not add an otherwise empty satellite hex outside the viable route set', () => {
    const emptyHex: Hex = {
      coord: { q: 0, r: 0 },
      planet: null,
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    act(() => useGameStore.getState().actions.selectAction('FormFederation'));
    render(
      <GameBoard
        board={{
          sectors: [],
          hexes: { '0,0': emptyHex },
          lost_planet: null,
          spaceship_tiles: {},
        }}
        interactivePlayerId={0}
        federationSelectableHexes={[]}
      />,
    );

    fireEvent.click(screen.getByLabelText('hex 0,0'));
    expect(useGameStore.getState().selectedHexes).toEqual([]);
  });

  it('opens the normal planet popup while a terraforming power action is active', () => {
    const hex: Hex = {
      coord: { q: 0, r: 0 },
      planet: { planet_type: 'Desert', is_gaia_formed: false, owner: null },
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    const onPlanetClick = vi.fn();
    act(() => useGameStore.getState().actions.selectPowerAction(2));
    render(
      <GameBoard
        board={{
          sectors: [],
          hexes: { '0,0': hex },
          lost_planet: null,
          spaceship_tiles: {},
        }}
        allowPlanetPopupDuringSelectedAction
        onPlanetClick={onPlanetClick}
      />,
    );

    fireEvent.click(screen.getByLabelText('hex 0,0'));
    expect(onPlanetClick).toHaveBeenCalledWith(hex, expect.objectContaining({ x: 0, y: 0 }));
    expect(useGameStore.getState().activePlanet).toBeNull();
  });

  it('opens spaceship exploration directly from a spaceship map tile', () => {
    const hex: Hex = {
      coord: { q: 2, r: -1 },
      planet: null,
      space_tile_kind: null,
      structures: [],
      satellites: [],
    };
    const onSpaceshipClick = vi.fn();
    render(
      <GameBoard
        board={{
          sectors: [],
          hexes: { '2,-1': hex },
          lost_planet: null,
          spaceship_tiles: { Twilight: { q: 2, r: -1 } },
        }}
        onSpaceshipClick={onSpaceshipClick}
      />,
    );

    fireEvent.click(screen.getByLabelText('hex 2,-1'), { clientX: 120, clientY: 240 });
    expect(onSpaceshipClick).toHaveBeenCalledWith('Twilight', { x: 120, y: 240 });
  });

});
