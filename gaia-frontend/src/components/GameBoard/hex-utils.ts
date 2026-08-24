// Flat-top hexagon coordinate math (axial → pixel)

export function axialToPixel(
  q: number,
  r: number,
  size: number,
): [number, number] {
  const x = size * (3 / 2) * q;
  const y = size * (Math.sqrt(3) / 2 * q + Math.sqrt(3) * r);
  return [x, y];
}

export function hexCorners(
  cx: number,
  cy: number,
  size: number,
): string {
  const points: string[] = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i); // flat-top: start at 0°
    const x = cx + size * Math.cos(angle);
    const y = cy + size * Math.sin(angle);
    points.push(`${x.toFixed(2)},${y.toFixed(2)}`);
  }
  return points.join(' ');
}

export function hexKey(q: number, r: number): string {
  return `${q},${r}`;
}

// Sector origin offset for placement on the board
export function sectorOriginPixel(
  origin: { q: number; r: number },
  size: number,
): [number, number] {
  return axialToPixel(origin.q, origin.r, size);
}
