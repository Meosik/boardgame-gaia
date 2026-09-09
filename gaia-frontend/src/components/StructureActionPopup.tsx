import {
  FACTION_STRUCTURE_COLOR,
  structureAssetName,
  structureImageSrc,
} from '../assets/structureImages';
import { standardTechTileImageSrc } from '../assets/techTileImages';
import { ResourceTokens } from './ResourceTokens';
import { axialDistance } from './GameBoard/hex-utils';
import type { BoardState, FactionId, HexCoord, PlayerState, StructureType } from '../types/game';

export type StructurePopupMode =
  | { kind: 'structure'; structure: StructureType; faction: FactionId | null }
  | { kind: 'choose-tech' }
  | { kind: 'choose-track' }
  | { kind: 'choose-cover'; tileIds: number[] }
  | { kind: 'choose-bonus-mine' };

interface Props {
  anchor: { x: number; y: number };
  coord: HexCoord;
  mode: StructurePopupMode;
  onUpgrade?: (to: StructureType) => void;
  onStartFederation?: () => void;
  onCoverTile?: (tileId: number) => void;
  onSkipResearch?: () => void;
  player?: PlayerState;
  board?: BoardState;
  onClose: () => void;
}

interface UpgradeOption {
  label: string;
  to: StructureType;
}

export function upgradeOptionsFor(
  structure: StructureType,
  faction: FactionId | null,
): UpgradeOption[] {
  if (structure === 'Mine') {
    return [{ label: '교역소', to: 'TradingStation' }];
  }
  if (structure === 'TradingStation') {
    return faction === 'Bescods'
      ? [
          { label: '과학 아카데미', to: { Academy: 'Science' } },
          { label: '정보 큐브 아카데미', to: { Academy: 'Qic' } },
        ]
      : [
          { label: '연구소', to: 'ResearchLab' },
          { label: '행성의회', to: 'PlanetaryInstitute' },
        ];
  }
  if (structure === 'ResearchLab') {
    return faction === 'Bescods'
      ? [{ label: '행성의회', to: 'PlanetaryInstitute' }]
      : [
          { label: '과학 아카데미', to: { Academy: 'Science' } },
          { label: '정보 큐브 아카데미', to: { Academy: 'Qic' } },
        ];
  }
  return [];
}

export function upgradeCostFor(
  from: StructureType,
  to: StructureType,
  mineHasOpponentNeighbor: boolean,
): { ore: number; credits: number } {
  if (from === 'Mine' && to === 'TradingStation') {
    return { ore: 2, credits: mineHasOpponentNeighbor ? 3 : 6 };
  }
  if (from === 'TradingStation' && to === 'ResearchLab') return { ore: 3, credits: 5 };
  if (from === 'TradingStation' && to === 'PlanetaryInstitute') return { ore: 4, credits: 6 };
  if (
    (from === 'ResearchLab' && typeof to === 'object')
    || (from === 'TradingStation' && typeof to === 'object')
  ) {
    return { ore: 6, credits: 6 };
  }
  if (from === 'ResearchLab' && to === 'PlanetaryInstitute') return { ore: 4, credits: 6 };
  return { ore: 0, credits: 0 };
}

function targetPieceAvailable(player: PlayerState, to: StructureType): boolean {
  if (to === 'TradingStation') {
    return player.structures.filter(({ kind }) => kind === 'TradingStation').length < 4;
  }
  if (to === 'ResearchLab') {
    return player.structures.filter(({ kind }) => kind === 'ResearchLab').length < 3;
  }
  if (to === 'PlanetaryInstitute') {
    return !player.structures.some(({ kind }) => kind === 'PlanetaryInstitute');
  }
  if (typeof to === 'object') {
    return player.structures.filter(({ kind }) => typeof kind === 'object').length < 2;
  }
  return true;
}

export function canPayForUpgrade(
  player: PlayerState,
  board: BoardState,
  coord: HexCoord,
  from: StructureType,
  to: StructureType,
): boolean {
  const mineHasOpponentNeighbor = from === 'Mine' && Object.values(board.hexes).some((hex) => (
    axialDistance(hex.coord, coord) <= 2
    && hex.structures.some(({ owner }) => owner !== player.player_id)
  ));
  const cost = upgradeCostFor(from, to, mineHasOpponentNeighbor);
  return targetPieceAvailable(player, to)
    && player.resources.ore >= cost.ore
    && player.resources.credits >= cost.credits;
}

export function StructureActionPopup({
  anchor,
  coord,
  mode,
  onUpgrade,
  onStartFederation,
  onCoverTile,
  onSkipResearch,
  player,
  board,
  onClose,
}: Props) {
  const width = 252;
  const left = Math.max(12, Math.min(anchor.x + 14, window.innerWidth - width - 12));
  const top = Math.max(56, Math.min(anchor.y - 32, window.innerHeight - 260));
  const options = mode.kind === 'structure'
    ? upgradeOptionsFor(mode.structure, mode.faction)
    : [];

  return (
    <div
      className="structure-action-popup"
      style={{ left, top, width }}
      role="dialog"
      aria-label={`구조물 행동 ${coord.q},${coord.r}`}
    >
      <button
        type="button"
        className="structure-action-popup__close"
        onClick={onClose}
        aria-label="구조물 행동 닫기"
      >
        ×
      </button>

      {mode.kind === 'structure' && (
        <>
          <div className="structure-action-popup__eyebrow">{coord.q}, {coord.r}</div>
          <div className="structure-action-popup__choices">
            {options.map(({ label, to }) => {
              const asset = structureAssetName(to);
              const color = mode.faction ? FACTION_STRUCTURE_COLOR[mode.faction] : 'gray';
              if (!asset) return null;
              const mineHasOpponentNeighbor = mode.structure === 'Mine' && player && board
                ? Object.values(board.hexes).some((hex) => (
                    axialDistance(hex.coord, coord) <= 2
                    && hex.structures.some(({ owner }) => owner !== player.player_id)
                  ))
                : false;
              const cost = upgradeCostFor(mode.structure, to, Boolean(mineHasOpponentNeighbor));
              const unavailable = player && board
                ? !canPayForUpgrade(player, board, coord, mode.structure, to)
                : false;
              return (
                <button
                  key={label}
                  type="button"
                  className="structure-action-popup__choice"
                  disabled={unavailable}
                  title={unavailable ? '필요 자원 또는 건물 말이 부족합니다.' : undefined}
                  onClick={() => onUpgrade?.(to)}
                >
                  <img src={structureImageSrc(color, asset)} alt="" />
                  <span>{label}</span>
                  <ResourceTokens
                    compact
                    label={`${label} 비용: 광석 ${cost.ore}, 크레딧 ${cost.credits}`}
                    values={cost}
                  />
                </button>
              );
            })}
            <button
              type="button"
              className="structure-action-popup__choice structure-action-popup__choice--federation"
              onClick={onStartFederation}
            >
              <span className="structure-action-popup__satellite">◆</span>
              <span>연방</span>
            </button>
          </div>
        </>
      )}

      {mode.kind === 'choose-tech' && (
        <PopupInstruction eyebrow="업그레이드" text="연구판에서 기술 타일을 누르세요" />
      )}
      {mode.kind === 'choose-track' && (
        <>
          <PopupInstruction eyebrow="연구 상승" text="연구판에서 올릴 트랙을 누르세요" />
          <button type="button" className="btn btn-ghost" onClick={onSkipResearch}>
            연구 상승 없이 완료
          </button>
        </>
      )}
      {mode.kind === 'choose-bonus-mine' && (
        <PopupInstruction eyebrow="무료 광산" text="게임 보드에서 행성을 누르세요" />
      )}
      {mode.kind === 'choose-cover' && (
        <>
          <PopupInstruction eyebrow="고급 기술" text="덮을 내 표준 기술을 고르세요" />
          <div className="structure-action-popup__tech-list">
            {mode.tileIds.map((tileId) => (
              <button
                key={tileId}
                type="button"
                className="structure-action-popup__tech"
                onClick={() => onCoverTile?.(tileId)}
                aria-label={`표준 기술 타일 ${tileId} 덮기`}
              >
                <img src={standardTechTileImageSrc(tileId)} alt={`표준 기술 타일 ${tileId}`} />
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function PopupInstruction({ eyebrow, text }: { eyebrow: string; text: string }) {
  return (
    <div className="structure-action-popup__instruction">
      <span>{eyebrow}</span>
      <strong>{text}</strong>
    </div>
  );
}
