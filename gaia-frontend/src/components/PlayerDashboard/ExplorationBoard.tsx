import { explorationBoardImageSrc } from '../../assets/explorationBoardImages';
import type { FactionId } from '../../types/game';
import { FACTION_VISUAL } from '../GameLobby/FactionBadge';

const EXPLORATION_SHUTTLE_COUNT = 3;

interface Props {
  faction: FactionId;
  shuttlesAvailable: number;
}

/**
 * Lost Fleet personal Exploration Board. The printed board contains three
 * shuttle silhouettes; code-native tokens are layered over the silhouettes
 * while those shuttles remain available to deploy.
 */
export function ExplorationBoard({ faction, shuttlesAvailable }: Props) {
  const imageSrc = explorationBoardImageSrc(faction);
  const available = Math.max(0, Math.min(EXPLORATION_SHUTTLE_COUNT, shuttlesAvailable));
  const factionColor = FACTION_VISUAL[faction].color;

  if (!imageSrc) return null;

  return (
    <figure
      className="exploration-board"
      aria-label={`${faction} 탐사 보드, 사용 가능한 셔틀 ${available}개`}
    >
      <div className="exploration-board-image-wrap">
        <img className="exploration-board-image" src={imageSrc} alt={`${faction} 탐사 보드`} />
        {[0, 1, 2].map((slot) => (
          slot < available ? (
            <span
              key={slot}
              className={`exploration-shuttle exploration-shuttle--${slot + 1}`}
              style={{ '--shuttle-color': factionColor } as React.CSSProperties}
              aria-label={`대기 중인 탐사 셔틀 ${slot + 1}`}
            >
              <span aria-hidden>◆</span>
            </span>
          ) : null
        ))}
      </div>
      <figcaption>셔틀 {available}/{EXPLORATION_SHUTTLE_COUNT}</figcaption>
    </figure>
  );
}
