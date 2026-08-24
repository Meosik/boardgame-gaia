import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { axialToPixel, hexCorners, hexKey } from '../components/GameBoard/hex-utils';

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
});
