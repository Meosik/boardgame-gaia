import { FACTION_TIPS } from '../factionTips';
import { factionDisplayName } from '../displayNames';
import type { FactionId } from '../types/game';

interface Props {
  faction: FactionId;
  /** Open from the start (the create-room view); in the game it starts folded. */
  defaultOpen?: boolean;
}

/** A foldable reminder of one faction: its board ability, its planetary institute ability
 * (rulebook appendices) and the guides' research tracks and round-1 builds (advice). */
export function FactionTipCard({ faction, defaultOpen = false }: Props) {
  const tip = FACTION_TIPS[faction];
  return (
    <details className="faction-tip-card" open={defaultOpen}>
      <summary>{factionDisplayName(faction)} 종족 팁</summary>
      <dl>
        <dt>종족 능력</dt>
        <dd>{tip.ability}</dd>
        <dt>의회 능력</dt>
        <dd>{tip.institute}</dd>
        <dt>가이드 연구 트랙</dt>
        <dd>{tip.tracks}</dd>
        <dt>가이드 1라운드 건물</dt>
        <dd>{tip.opening}</dd>
      </dl>
      <small>능력은 룰북, 연구 트랙·건물은 공략 글 요약(앞쪽이 저자 선호)입니다.</small>
    </details>
  );
}
