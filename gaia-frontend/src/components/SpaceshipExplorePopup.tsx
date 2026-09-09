import { useState } from 'react';
import { explorationShuttleImageSrc } from '../assets/explorationShuttleImages';
import { informationCubesNeededForRange } from './PlanetActionPopup';
import type { BoardState, PlayerState, SpaceshipBoard, SpaceshipId } from '../types/game';

interface Props {
  anchor: { x: number; y: number };
  ship: SpaceshipId;
  spaceshipBoard: SpaceshipBoard;
  board: BoardState;
  player: PlayerState;
  selectedRangeQic: number;
  onConfirm: () => void;
  onClose: () => void;
}

const SHIP_LABEL: Record<SpaceshipId, string> = {
  Twilight: 'Twilight',
  Rebellion: 'Rebellion',
  TFMars: 'T F Mars',
  Eclipse: 'Eclipse',
};

export interface SpaceshipExploreStatus {
  available: boolean;
  reason: string;
  rangeQic: number | null;
  slot: number;
  powerCharge: number;
}

export function spaceshipExploreStatus(
  board: BoardState,
  spaceshipBoard: SpaceshipBoard,
  player: PlayerState,
  selectedRangeQic: number,
): SpaceshipExploreStatus {
  const target = board.spaceship_tiles[spaceshipBoard.id];
  const rangeQic = target ? informationCubesNeededForRange(board, player, target) : null;
  const slotIndex = spaceshipBoard.explorers.findIndex((explorer) => explorer === null);
  const slot = slotIndex + 1;
  const powerCharge = [0, 2, 2, 3][slotIndex] ?? 0;
  const status = (available: boolean, reason: string): SpaceshipExploreStatus => ({
    available,
    reason,
    rangeQic,
    slot,
    powerCharge,
  });

  if (player.exploration_shuttles_available < 1) return status(false, '사용할 수 있는 탐사선이 없습니다.');
  if (spaceshipBoard.explorers.includes(player.player_id)) return status(false, '이미 이 함선을 탐사했습니다.');
  if (slotIndex < 0) return status(false, '이 함선의 탐사선 슬롯이 모두 찼습니다.');
  if (!target || rangeQic === null) return status(false, '이 함선까지의 사거리를 계산할 수 없습니다.');
  if (player.resources.qic < rangeQic) return status(false, `정보 큐브 ${rangeQic}개가 필요합니다.`);
  if (selectedRangeQic < rangeQic) {
    return status(false, `우측에서 정보 큐브를 ${rangeQic - selectedRangeQic}개 더 추가하세요.`);
  }
  if (player.vp < 5) return status(false, '함선 탐사에는 승점 5점이 필요합니다.');
  if (player.faction === 'Taklons'
    && !['Area1', 'Area2', 'Area3'].includes(player.resources.power.brainstone ?? '')) {
    return status(false, '타클론은 브레인스톤이 활성 파워 영역에 있어야 합니다.');
  }
  return status(true, '함선 탐사 가능');
}

export function SpaceshipExplorePopup({
  anchor,
  ship,
  spaceshipBoard,
  board,
  player,
  selectedRangeQic,
  onConfirm,
  onClose,
}: Props) {
  const [confirming, setConfirming] = useState(false);
  const status = spaceshipExploreStatus(board, spaceshipBoard, player, selectedRangeQic);
  const width = 252;
  const left = Math.max(12, Math.min(anchor.x + 14, window.innerWidth - width - 12));
  const top = Math.max(56, Math.min(anchor.y - 32, window.innerHeight - 280));

  return (
    <>
      <button type="button" className="board-context-popup-scrim" aria-label="함선 탐사 취소" onClick={onClose} />
      <aside
        className="structure-action-popup spaceship-explore-popup"
        style={{ left, top, width }}
        role="dialog"
        aria-label={`${SHIP_LABEL[ship]} 함선 탐사`}
      >
        {!confirming ? (
          <>
            <button
              type="button"
              className="planet-rulebook-action"
              disabled={!status.available}
              onClick={() => setConfirming(true)}
              aria-label="함선 탐사"
            >
              <span className="planet-rulebook-action__primary">
                <img src={explorationShuttleImageSrc(player.faction)} alt="" aria-hidden="true" />
                <strong>함선 탐사</strong>
              </span>
              <span className="spaceship-explore-summary">
                <b>승점 5점</b>
                {(status.rangeQic ?? 0) > 0 && <b>정보 큐브 {status.rangeQic}개</b>}
              </span>
            </button>
            <p className={`spaceship-explore-status${status.available ? ' is-valid' : ''}`} role="status">
              {status.reason}
            </p>
          </>
        ) : (
          <>
            <div className="interaction-selection-title interaction-selection-title--source">
              <img
                className="spaceship-explore-shuttle"
                src={explorationShuttleImageSrc(player.faction)}
                alt=""
                aria-hidden="true"
              />
              <div><small>{SHIP_LABEL[ship]}</small><h3>함선 탐사</h3></div>
            </div>
            <div className="spaceship-explore-costs" aria-label="함선 탐사 비용">
              <span>탐사선 <strong>1개</strong></span>
              <span>승점 <strong>5점</strong></span>
              {(status.rangeQic ?? 0) > 0 && <span>정보 큐브 <strong>{status.rangeQic}개</strong></span>}
            </div>
            <p className="spaceship-explore-slot">
              {status.slot}번 슬롯에 배치
              {status.powerCharge > 0 ? ` · 파워 ${status.powerCharge} 충전` : ''}
            </p>
            <div className="terraform-ore-confirmation__actions">
              <button type="button" onClick={() => setConfirming(false)}>돌아가기</button>
              <button type="button" className="interaction-confirm" onClick={onConfirm}>함선 탐사 확정</button>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
