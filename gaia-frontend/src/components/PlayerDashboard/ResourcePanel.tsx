import type { Resources } from '../../types/game';

interface Props {
  resources: Resources;
}

export function ResourcePanel({ resources }: Props) {
  return (
    <div className="resource-panel">
      <ResourceRow label="광석" value={resources.ore} icon="⛏" />
      <ResourceRow label="크레딧" value={resources.credits} icon="💰" />
      <ResourceRow label="지식" value={resources.knowledge} icon="🔬" />
      <ResourceRow label="QIC" value={resources.qic} icon="⚡" />
    </div>
  );
}

function ResourceRow({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="resource-row">
      <span className="resource-icon">{icon}</span>
      <span className="resource-label">{label}</span>
      <span className="resource-value">{value}</span>
    </div>
  );
}
