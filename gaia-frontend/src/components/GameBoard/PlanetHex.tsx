import type { PlanetType } from '../../types/game';

import { planetImageSrc } from '../../assets/planetImages';

const PLANET_VISUAL: Record<PlanetType, { color: string; ring?: boolean }> = {
  Terra:       { color: '#4a7c59' },
  Desert:      { color: '#c4a35a' },
  Ice:         { color: '#a8d4e6' },
  Swamp:       { color: '#5d4037' },
  Oxide:       { color: '#c62828' },
  Titanium:    { color: '#546e7a' },
  Volcanic:    { color: '#e64a19' },
  Transdim:    { color: '#7b1fa2', ring: true },
  Gaia:        { color: '#0097a7' },
  LostPlanet:  { color: '#4e342e' },
  Asteroid:    { color: '#78909c' },
  ProtoPlanet: { color: '#81c784' },
};

interface Props {
  planetType: PlanetType;
  cx: number;
  cy: number;
  size: number;
  hexKey?: string;
}

export function PlanetHex({ planetType, cx, cy, size, hexKey = '' }: Props) {
  // Gaia overlays replace printed sector planets, rather than decorating their centers.
  const r = size * (planetType === 'Gaia' ? 0.68 : 0.3);
  // gaia.png is 528px wide, but the planet occupies only x/y 38..490.
  // Scale past that transparent margin so the visible planet fills the overlay.
  const imageRadius = planetType === 'Gaia' ? r * 528 / 452 : r;
  const vis = PLANET_VISUAL[planetType];
  const img = planetImageSrc(planetType);

  if (img) {
    const clipId = `planet-clip-${hexKey}`;
    return (
      <g>
        <defs>
          <clipPath id={clipId}>
            <circle cx={cx} cy={cy} r={r} />
          </clipPath>
        </defs>
        <circle cx={cx} cy={cy} r={r} fill="#000" />
        <image
          href={img}
          x={cx - imageRadius}
          y={cy - imageRadius}
          width={imageRadius * 2}
          height={imageRadius * 2}
          clipPath={`url(#${clipId})`}
          preserveAspectRatio="xMidYMid slice"
        />
        {vis.ring && (
          <ellipse
            cx={cx}
            cy={cy}
            rx={r * 1.55}
            ry={r * 0.32}
            fill="none"
            stroke={vis.color}
            strokeWidth={1.2}
            opacity={0.65}
          />
        )}
      </g>
    );
  }

  return (
    <g>
      <circle cx={cx} cy={cy} r={r} fill={vis.color} stroke="#000" strokeWidth={0.5} />
      <ellipse
        cx={cx + r * 0.22}
        cy={cy + r * 0.18}
        rx={r * 0.68}
        ry={r * 0.58}
        fill="rgba(0,0,0,0.32)"
      />
      <ellipse
        cx={cx - r * 0.22}
        cy={cy - r * 0.18}
        rx={r * 0.26}
        ry={r * 0.17}
        fill="rgba(255,255,255,0.42)"
      />
      {vis.ring && (
        <ellipse
          cx={cx}
          cy={cy}
          rx={r * 1.55}
          ry={r * 0.32}
          fill="none"
          stroke={vis.color}
          strokeWidth={1.2}
          opacity={0.65}
        />
      )}
    </g>
  );
}
