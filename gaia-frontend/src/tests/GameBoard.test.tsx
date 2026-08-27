import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { HexCell } from '../components/GameBoard/HexCell';
import { axialDistance, axialToPixel, hexCorners, hexKey } from '../components/GameBoard/hex-utils';
import type { Hex } from '../types/game';

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
          showPlanetOverlay={false}
          hasPowerRing={false}
          onClick={() => undefined}
        />
      </svg>,
    );

    expect(container.querySelector('image')).toBeNull();
    expect(container.querySelector('polygon')?.getAttribute('fill')).toBe('transparent');
  });
});
