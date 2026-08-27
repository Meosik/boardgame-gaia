import oreIcon from '../../assets/icons/ore.png';
import creditsIcon from '../../assets/icons/credits.png';
import knowledgeIcon from '../../assets/icons/knowledge.png';
import qicIcon from '../../assets/icons/qic.png';
import type { Resources } from '../../types/game';

interface Props {
  resources: Resources;
}

export function ResourcePanel({ resources }: Props) {
  return (
    <div className="resource-panel">
      <ResourceRow label="광석" value={resources.ore} icon={oreIcon} />
      <ResourceRow label="크레딧" value={resources.credits} icon={creditsIcon} />
      <ResourceRow label="지식" value={resources.knowledge} icon={knowledgeIcon} />
      <ResourceRow label="QIC" value={resources.qic} icon={qicIcon} />
    </div>
  );
}

function ResourceRow({ label, value, icon }: { label: string; value: number; icon: string }) {
  return (
    <div className="resource-row">
      <img className="resource-icon" src={icon} alt="" />
      <span className="resource-label">{label}</span>
      <span className="resource-value">{value}</span>
    </div>
  );
}
