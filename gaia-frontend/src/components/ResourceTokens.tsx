import { GamePieceIcon, type GamePieceIconKind } from './GamePieceIcon';

export type DisplayResource = 'ore' | 'credits' | 'knowledge' | 'qic' | 'power';

const RESOURCE_DISPLAY: Record<DisplayResource, { icon: GamePieceIconKind; label: string }> = {
  ore: { icon: 'ore', label: '광석' },
  credits: { icon: 'credits', label: '크레딧' },
  knowledge: { icon: 'knowledge', label: '지식' },
  qic: { icon: 'qic', label: '정보 큐브' },
  power: { icon: 'power', label: '파워' },
};

interface ResourceTokenProps {
  resource: DisplayResource;
  value: number;
  compact?: boolean;
}

export function ResourceToken({ resource, value, compact = false }: ResourceTokenProps) {
  const { icon, label } = RESOURCE_DISPLAY[resource];
  return (
    <span
      className={`interaction-resource-token interaction-resource-token--${resource}${
        compact ? ' interaction-resource-token--compact' : ''
      }`}
      aria-label={`${label} ${value}`}
      title={`${label} ${value}`}
    >
      <GamePieceIcon kind={icon} />
      <strong>{value}</strong>
    </span>
  );
}

interface ResourceTokensProps {
  values: Partial<Record<DisplayResource, number>>;
  compact?: boolean;
  label: string;
}

export function ResourceTokens({ values, compact = false, label }: ResourceTokensProps) {
  return (
    <span className="interaction-resource-tokens" aria-label={label}>
      {(Object.entries(values) as [DisplayResource, number][]).map(([resource, value]) => (
        <ResourceToken key={resource} resource={resource} value={value} compact={compact} />
      ))}
    </span>
  );
}

export function VictoryPointToken({ value }: { value: number }) {
  return (
    <span
      className="victory-point-token"
      aria-label={`승점 ${value}점`}
      title={`승점 ${value}점`}
    >
      <GamePieceIcon kind="vp" />
      <strong>{value}</strong>
    </span>
  );
}
