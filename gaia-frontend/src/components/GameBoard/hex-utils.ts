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

export function axialDistance(
  a: { q: number; r: number },
  b: { q: number; r: number },
): number {
  const dq = Math.abs(a.q - b.q);
  const dr = Math.abs(a.r - b.r);
  const ds = Math.abs((-a.q - a.r) - (-b.q - b.r));
  return Math.max(dq, dr, ds);
}

// Sector origin offset for placement on the board
export function sectorOriginPixel(
  origin: { q: number; r: number },
  size: number,
): [number, number] {
  return axialToPixel(origin.q, origin.r, size);
}

/** Mirrors `gaia_engine::game_state::HexCoord::rotate_60`/`rotate_n` exactly
 * (same `(q, r) -> (-r, q + r)` step, repeated `n % 6` times) — must stay in
 * lockstep with that implementation, since it's used to reproduce where a
 * sector's hexes actually landed on the board (`insert_sector` applies the
 * identical rotation to each of a sector template's relative hex offsets)
 * purely from `Sector.origin`/`Sector.rotation`, without needing the
 * resulting world coordinates to be looked up from `board.hexes`. */
export function rotateHexN(q: number, r: number, n: number): [number, number] {
  let rq = q;
  let rr = r;
  for (let i = 0; i < ((n % 6) + 6) % 6; i++) {
    const nextQ = -rr;
    const nextR = rq + rr;
    rq = nextQ;
    rr = nextR;
  }
  return [rq, rr];
}

/** Pixel centroid of a sector's hexes, given only its template's
 * origin-relative hex offsets (e.g. a 3-hex Deep Space L-tromino:
 * `[[0,0],[1,0],[0,1]]`, matching `gaia-engine/data/sectors.toml`) plus the
 * sector's actual `origin`/`rotation` — the same two numbers `insert_sector`
 * used to place its hexes on the real board, so this reproduces the same
 * positions without needing every deep-space sector's own hex list threaded
 * through as a prop. */
export function sectorCentroidPixel(
  relativeHexes: [number, number][],
  origin: { q: number; r: number },
  rotation: number,
  size: number,
): [number, number] {
  let sumX = 0;
  let sumY = 0;
  for (const [relQ, relR] of relativeHexes) {
    const [rq, rr] = rotateHexN(relQ, relR, rotation);
    const [x, y] = axialToPixel(rq + origin.q, rr + origin.r, size);
    sumX += x;
    sumY += y;
  }
  return [sumX / relativeHexes.length, sumY / relativeHexes.length];
}

/** Every hex's actual pixel position for a sector, given the same
 * origin-relative offsets `sectorCentroidPixel` takes — i.e. the same
 * per-hex positions `board.hexes` would show for this sector, reproduced
 * without needing to look them up. Used to build a clip region matching the
 * sector's real hex-cluster silhouette (a union of these hexagons) rather
 * than the background `<image>`'s own rectangular bounds, which — being a
 * plain rectangle regardless of `preserveAspectRatio` — would otherwise
 * paint a visibly square patch of the source photo's own background/corners
 * over the surrounding star field instead of blending into it. */
export function sectorHexPixelPositions(
  relativeHexes: [number, number][],
  origin: { q: number; r: number },
  rotation: number,
  size: number,
): [number, number][] {
  return relativeHexes.map(([relQ, relR]) => {
    const [rq, rr] = rotateHexN(relQ, relR, rotation);
    return axialToPixel(rq + origin.q, rr + origin.r, size);
  });
}

/** The 19 relative axial offsets of a radius-2 hex disk (flat-top), i.e.
 * every `(q, r)` with `max(|q|, |r|, |q + r|) <= 2` — a standard Space
 * Sector's shape (`gaia-engine/data/sectors.toml`), and exactly the same
 * disk `axialDistance(hex, sector.origin) <= 2` elsewhere in this codebase
 * already treats as "this sector's hexes". Generated rather than
 * hand-listed so the two stay trivially in sync. */
export const STANDARD_HEX_OFFSETS: [number, number][] = (() => {
  const offsets: [number, number][] = [];
  for (let q = -2; q <= 2; q++) {
    const rMin = Math.max(-2, -2 - q);
    const rMax = Math.min(2, 2 - q);
    for (let r = rMin; r <= rMax; r++) {
      offsets.push([q, r]);
    }
  }
  return offsets;
})();
