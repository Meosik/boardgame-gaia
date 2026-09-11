import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { PlanetHex } from '../components/GameBoard/PlanetHex';

describe('PlanetHex', () => {
  it('renders the Gaia image without a synthetic blue ring', () => {
    const { container } = render(
      <svg><PlanetHex planetType="Gaia" cx={50} cy={50} size={40} hexKey="1,0" /></svg>,
    );
    expect(container.querySelector('image')?.getAttribute('href')).toContain('gaia.png');
    expect(container.querySelector('ellipse')).toBeNull();
    expect(Number(container.querySelector('clipPath circle')?.getAttribute('r'))).toBeCloseTo(40 * 0.68);
    expect(Number(container.querySelector('image')?.getAttribute('width')))
      .toBeCloseTo(40 * 0.68 * 2 * 528 / 452);
    expect(container.querySelector('g > circle')?.getAttribute('fill')).toBe('#000');
  });

  it('preserves the unrelated Transdim ring', () => {
    const { container } = render(
      <svg><PlanetHex planetType="Transdim" cx={50} cy={50} size={40} hexKey="1,0" /></svg>,
    );
    expect(container.querySelector('ellipse')?.getAttribute('stroke')).toBe('#7b1fa2');
  });
});
