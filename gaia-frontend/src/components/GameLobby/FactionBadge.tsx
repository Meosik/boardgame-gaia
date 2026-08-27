import type { FactionId } from '../../types/game';

export const FACTION_VISUAL: Record<FactionId, { color: string; initials: string }> = {
  Terrans:      { color: '#4a7c59', initials: 'TE' },
  Lantids:      { color: '#9575cd', initials: 'LA' },
  Xenos:        { color: '#9b59b6', initials: 'XE' },
  Gleens:       { color: '#81c784', initials: 'GL' },
  Taklons:      { color: '#ff8a65', initials: 'TK' },
  Ambas:        { color: '#4fc3f7', initials: 'AM' },
  HadschHallas: { color: '#ffd54f', initials: 'HH' },
  Ivits:        { color: '#e57373', initials: 'IV' },
  Geodens:      { color: '#aed581', initials: 'GE' },
  BalTaks:      { color: '#ff7043', initials: 'BT' },
  Firaks:       { color: '#ba68c8', initials: 'FI' },
  Bescods:      { color: '#90a4ae', initials: 'BC' },
  Nevlas:       { color: '#80deea', initials: 'NV' },
  Itars:        { color: '#ffb74d', initials: 'IT' },
  Tinkeroids:   { color: '#64b5f6', initials: 'TR' },
  Moweyds:      { color: '#a5d6a7', initials: 'MW' },
  SpaceGiants:  { color: '#ffe082', initials: 'SG' },
  Darkanians:   { color: '#ef9a9a', initials: 'DK' },
};

interface Props {
  faction: FactionId;
  onSelect?: (f: FactionId) => void;
  /** Badge circle diameter in px (default: 28) */
  size?: number;
  /** Show faction name label next to the badge circle (default: true) */
  showLabel?: boolean;
  /**
   * TTS image swap point.
   * Provide a URL to render an <img> instead of the SVG circle + initials.
   */
  imageSrc?: string;
}

export function FactionBadge({
  faction,
  onSelect,
  size = 28,
  showLabel = true,
  imageSrc,
}: Props) {
  const vis = FACTION_VISUAL[faction];
  const r = size / 2;

  const circle = imageSrc ? (
    <img
      src={imageSrc}
      alt={faction}
      width={size}
      height={size}
      // Exploration Board portraits are 480x1332 with the character art in a
      // ~480x480 band starting ~60px (~7% of the 852px vertical overflow
      // once cover-scaled to a square) from the top — the default 50%
      // vertical center instead lands on the stats table in the board's
      // midsection. Verified against terraner/ambas/bal_t_ak/lantida/itar
      // crops at this offset: face fully visible and centered for all.
      style={{ borderRadius: '50%', objectFit: 'cover', objectPosition: '50% 7%', display: 'block' }}
    />
  ) : (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
      <circle cx={r} cy={r} r={r - 1} fill={vis.color} />
      {/* specular highlight */}
      <ellipse
        cx={r * 0.65}
        cy={r * 0.62}
        rx={r * 0.38}
        ry={r * 0.25}
        fill="rgba(255,255,255,0.35)"
      />
      <text
        x={r}
        y={r}
        dominantBaseline="central"
        textAnchor="middle"
        fontSize={size * 0.34}
        fontWeight="700"
        fill="#fff"
        fontFamily="system-ui, sans-serif"
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {vis.initials}
      </text>
    </svg>
  );

  const cssVar = { '--faction-color': vis.color } as React.CSSProperties;

  if (!onSelect) {
    return (
      <span className="faction-badge" style={cssVar}>
        {circle}
        {showLabel && <span className="faction-badge-label">{faction}</span>}
      </span>
    );
  }

  return (
    <button
      className="faction-badge faction-badge--btn"
      style={cssVar}
      onClick={(e) => { e.stopPropagation(); onSelect(faction); }}
      title={faction}
    >
      {circle}
      {showLabel && <span className="faction-badge-label">{faction}</span>}
    </button>
  );
}
