import { GamePieceIcon, type GamePieceIconKind } from '../GamePieceIcon';
import type { Resources } from '../../types/game';

interface Props {
  resources: Resources;
  placement?: 'summary' | 'faction-board';
}

export function ResourcePanel({ resources, placement = 'summary' }: Props) {
  return (
    <div
      className={`resource-panel resource-panel--${placement}`}
      aria-label={placement === 'faction-board' ? '현재 자원' : undefined}
    >
      <ResourceRow kind="ore" label="광석" value={resources.ore} icon="ore" />
      <ResourceRow kind="credits" label="크레딧" value={resources.credits} icon="credits" />
      <ResourceRow kind="knowledge" label="지식" value={resources.knowledge} icon="knowledge" />
      <ResourceRow kind="qic" label="정보 큐브" value={resources.qic} icon="qic" />
    </div>
  );
}

function ResourceRow({
  kind,
  label,
  value,
  icon,
}: {
  kind: 'ore' | 'credits' | 'knowledge' | 'qic';
  label: string;
  value: number;
  icon: GamePieceIconKind;
}) {
  return (
    <div className={`resource-row resource-row--${kind}`}>
      <GamePieceIcon className="resource-icon" kind={icon} />
      <span className="resource-label">{label}</span>
      <span className="resource-value">{value}</span>
    </div>
  );
}
