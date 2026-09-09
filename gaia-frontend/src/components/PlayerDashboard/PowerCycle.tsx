import type { FactionId, PowerCycle as PowerCycleData } from '../../types/game';
import { GamePieceIcon } from '../GamePieceIcon';

interface Props {
  power: PowerCycleData;
  faction?: FactionId | null;
}

const BOWL_LABELS = [
  { key: 'bowl1',     label: 'I'  },
  { key: 'bowl2',     label: 'II' },
  { key: 'bowl3',     label: 'III'},
  { key: 'gaia_bowl', label: 'G'  },
] as const;

const FALLBACK_COLORS: Record<string, string> = {
  I: '#546e7a', II: '#5c6bc0', III: '#7b1fa2', G: '#00838f', GF: '#2e7d32',
};

export function PowerCycle({ power, faction }: Props) {
  const brainstoneBowl =
    power.brainstone === 'Area1' ? 'I'
      : power.brainstone === 'Area2' ? 'II'
        : power.brainstone === 'Area3' ? 'III'
          : power.brainstone === 'Gaia' ? 'G'
            : null;

  return (
    <div className="power-cycle">
      {BOWL_LABELS.map(({ key, label }) => (
        <BowlDisplay
          key={key}
          label={label}
          count={power[key]}
          faction={faction ?? null}
          color={FALLBACK_COLORS[label]}
          hasBrainstone={brainstoneBowl === label}
        />
      ))}
      {power.gaia_forming > 0 && (
        <BowlDisplay
          label="GF"
          count={power.gaia_forming}
          faction={faction ?? null}
          color={FALLBACK_COLORS['GF']}
          hasBrainstone={false}
        />
      )}
    </div>
  );
}

function BowlDisplay({
  label,
  count,
  faction,
  color,
  hasBrainstone,
}: {
  label: string;
  count: number;
  faction: FactionId | null;
  color: string;
  hasBrainstone: boolean;
}) {
  return (
    <div className="power-bowl" style={{ borderColor: color }}>
      <span className="bowl-label" style={{ color }}>{label}</span>
      {faction ? (
        <div className="bowl-tokens">
          {Array.from({ length: count }).map((_, i) => (
            <GamePieceIcon
              key={i}
              kind="power"
              className="power-bowl-piece"
            />
          ))}
          {hasBrainstone && (
            <GamePieceIcon
              kind="brainstone"
              className="brainstone-token"
              decorative={false}
              label="브레인스톤"
              title="Taklons Brainstone"
            />
          )}
          {count === 0 && !hasBrainstone && <span className="bowl-empty">—</span>}
        </div>
      ) : (
        <span className="bowl-count">{count}</span>
      )}
    </div>
  );
}
