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
  rewardTarget?: boolean;
}

export function ResourceToken({ resource, value, compact = false, rewardTarget = false }: ResourceTokenProps) {
  const { icon, label } = RESOURCE_DISPLAY[resource];
  return (
    <span
      className={`interaction-resource-token interaction-resource-token--${resource}${
        compact ? ' interaction-resource-token--compact' : ''
      }`}
      data-reward-kind={rewardTarget ? resource : undefined}
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

export function VictoryPointToken({ value, rewardTarget = false }: { value: number; rewardTarget?: boolean }) {
  return (
    <span
      className="victory-point-token"
      data-reward-kind={rewardTarget ? 'vp' : undefined}
      aria-label={`승점 ${value}점`}
      title={`승점 ${value}점`}
    >
      <GamePieceIcon kind="vp" />
      <strong>{value}</strong>
    </span>
  );
}


export function GaiaPowerTransfer({ value }: { value: number }) {
  return (
    <span className="gaia-power-transfer" aria-label={`파워 ${value}개 → 가이아 구역`} title={`파워 ${value}개를 가이아 구역으로 이동`}>
      <ResourceToken resource="power" value={value} />
      <span aria-hidden="true">→</span>
      <span className="gaia-power-transfer-destination" aria-hidden="true">G</span>
    </span>
  );
}
