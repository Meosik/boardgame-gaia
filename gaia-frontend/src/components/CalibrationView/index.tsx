import { useRef, useState, type MouseEvent } from 'react';
import { spaceshipBoardImageSrc } from '../../assets/spaceshipBoardImages';
import { standardTechTileImageSrc, advancedTechTileImageSrc } from '../../assets/techTileImages';
import { artifactImageSrc } from '../../assets/artifactImages';
import { federationTokenImageSrc } from '../../assets/federationTokenImages';
import { researchBoardImageSrc } from '../../assets/researchBoardImage';
import { roundScoringTileImageSrc } from '../../assets/roundScoringTileImages';
import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import { scoringBoardImageSrc } from '../../assets/scoringBoardImage';
import { scoringBoardExtensionImageSrc } from '../../assets/scoringBoardExtensionImage';
import { lostFleetTechRequirementBoardImageSrc } from '../../assets/lostFleetTechRequirementBoardImages';
import { economyResearchTileImageSrc } from '../../assets/economyResearchTileImages';
import qicOverlayImageSrc from '../../assets/boards/normalized/lost_fleet_qic_board_overlay.webp';
import type { EconomyResearchTileSide, FactionId, SpaceshipId } from '../../types/game';

const QIC_OVERLAY_SRC = qicOverlayImageSrc;

type AssetCategory =
  | 'shipBoard'
  | 'standardTech'
  | 'advancedTech'
  | 'artifact'
  | 'federationToken'
  | 'researchBoard'
  | 'roundScoring'
  | 'factionBoard'
  | 'scoringBoard'
  | 'scoringBoardExtension'
  | 'lostFleetTechRequirement'
  | 'economyOverlay'
  | 'qicOverlay';

const SHIP_IDS: SpaceshipId[] = ['Eclipse', 'TFMars', 'Rebellion', 'Twilight'];
const ECONOMY_SIDES: EconomyResearchTileSide[] = ['Power', 'VictoryPoints'];

const FACTION_IDS: FactionId[] = [
  'Terrans', 'Lantids', 'Xenos', 'Gleens', 'Taklons', 'Ambas',
  'HadschHallas', 'Ivits', 'Geodens', 'BalTaks', 'Firaks', 'Bescods',
  'Nevlas', 'Itars', 'Tinkeroids', 'Moweyds', 'SpaceGiants', 'Darkanians',
];

const CATEGORY_LABEL: Record<AssetCategory, string> = {
  shipBoard: '함선 보드',
  standardTech: '표준 기술 타일',
  advancedTech: '고급 기술 타일',
  artifact: '아티팩트',
  federationToken: '연방 토큰',
  researchBoard: '연구 보드',
  roundScoring: '라운드 점수 타일',
  factionBoard: '종족 보드',
  scoringBoard: '점수 보드 (라운드·최종)',
  scoringBoardExtension: '라운드 목표 뒷 보드 (점수 보드 확장, 3/4인용 뒷면)',
  lostFleetTechRequirement: '고급 기술 조건 보드 (25VP/탐사선 3개, Lost Fleet 뒷면)',
  economyOverlay: '경제 연구 3·4레벨 대체 타일 (연구판 오버레이)',
  qicOverlay: 'Lost Fleet QIC 액션칸 폐쇄 오버레이 (연구판 오버레이)',
};

/** Categories with a single, ID-less image — no id selector should show for these. */
const NO_ID_CATEGORIES: ReadonlySet<AssetCategory> = new Set([
  'researchBoard',
  'scoringBoard',
  'scoringBoardExtension',
  'lostFleetTechRequirement',
  'qicOverlay',
]);

function resolveSrc(category: AssetCategory, id: string): string | undefined {
  switch (category) {
    case 'shipBoard':
      return spaceshipBoardImageSrc(id as SpaceshipId) ?? undefined;
    case 'standardTech':
      return standardTechTileImageSrc(Number(id));
    case 'advancedTech':
      return advancedTechTileImageSrc(Number(id));
    case 'artifact':
      return artifactImageSrc(Number(id));
    case 'federationToken':
      return federationTokenImageSrc(Number(id));
    case 'researchBoard':
      return researchBoardImageSrc();
    case 'roundScoring':
      return roundScoringTileImageSrc(Number(id));
    case 'factionBoard':
      return factionBoardImageSrc(id as FactionId) ?? undefined;
    case 'scoringBoard':
      return scoringBoardImageSrc();
    case 'scoringBoardExtension':
      return scoringBoardExtensionImageSrc();
    case 'lostFleetTechRequirement':
      // This project is fixed at 4 players, so this always renders the
      // "exploration-shuttles" (back) side — see engine.rs's setup, which
      // never selects the 2-player-only "25-vp" side.
      return lostFleetTechRequirementBoardImageSrc('exploration-shuttles');
    case 'economyOverlay':
      return economyResearchTileImageSrc(id as EconomyResearchTileSide);
    case 'qicOverlay':
      return QIC_OVERLAY_SRC;
    default:
      return undefined;
  }
}

interface Point {
  xPx: number;
  yPx: number;
  xPct: number;
  yPct: number;
}

// Several categories skip IDs the real game never uses (standard tech tiles
// start at 2, advanced tech tile 18 doesn't exist, federation token 7 is a
// deliberate gap) — hardcoding "1" as the landing ID after a category switch
// meant standard tech tiles, for instance, always opened on the one ID
// guaranteed to show nothing. Probing for the first ID that actually
// resolves keeps this correct even if the asset set changes again later.
function firstValidId(category: AssetCategory): string {
  if (category === 'shipBoard') return SHIP_IDS[0];
  if (category === 'factionBoard') return FACTION_IDS[0];
  if (category === 'economyOverlay') return ECONOMY_SIDES[0];
  for (let id = 1; id <= 30; id += 1) {
    if (resolveSrc(category, String(id))) return String(id);
  }
  return '1';
}

function CalibrationPanel({ title }: { title: string }) {
  const [category, setCategory] = useState<AssetCategory>('shipBoard');
  const [idInput, setIdInput] = useState<string>('Eclipse');
  const [points, setPoints] = useState<Point[]>([]);
  const imgRef = useRef<HTMLImageElement>(null);

  const src = resolveSrc(category, idInput);

  function handleCategoryChange(next: AssetCategory) {
    setCategory(next);
    setIdInput(firstValidId(next));
    setPoints([]);
  }

  function handleIdChange(next: string) {
    setIdInput(next);
    setPoints([]);
  }

  // Reading `naturalWidth`/`naturalHeight` — the source image's own pixel
  // dimensions — rather than the rendered box size is what makes the
  // reported point independent of however large this debug view happens to
  // display the image; it always matches "the pixel you'd land on if you
  // opened this same file in an image editor and zoomed in."
  function handleImageClick(e: MouseEvent<HTMLImageElement>) {
    const img = imgRef.current;
    if (!img) return;
    const rect = img.getBoundingClientRect();
    const xPct = ((e.clientX - rect.left) / rect.width) * 100;
    const yPct = ((e.clientY - rect.top) / rect.height) * 100;
    const xPx = Math.round((xPct / 100) * img.naturalWidth);
    const yPx = Math.round((yPct / 100) * img.naturalHeight);
    setPoints((prev) => [...prev, { xPx, yPx, xPct, yPct }]);
  }

  function undo() {
    setPoints((prev) => prev.slice(0, -1));
  }

  function reset() {
    setPoints([]);
  }

  function copyPoints() {
    const text = points.map((p) => `${p.xPx}, ${p.yPx}`).join('\n');
    void navigator.clipboard?.writeText(text);
  }

  return (
    <div className="calibration-panel">
      <h3>{title}</h3>
      <div className="calibration-controls">
        <select
          value={category}
          onChange={(e) => handleCategoryChange(e.target.value as AssetCategory)}
        >
          {Object.entries(CATEGORY_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {category === 'shipBoard' ? (
          <select value={idInput} onChange={(e) => handleIdChange(e.target.value)}>
            {SHIP_IDS.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        ) : category === 'factionBoard' ? (
          <select value={idInput} onChange={(e) => handleIdChange(e.target.value)}>
            {FACTION_IDS.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        ) : category === 'economyOverlay' ? (
          <select value={idInput} onChange={(e) => handleIdChange(e.target.value)}>
            {ECONOMY_SIDES.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        ) : NO_ID_CATEGORIES.has(category) ? null : (
          <input
            type="number"
            min={1}
            value={idInput}
            onChange={(e) => handleIdChange(e.target.value)}
            className="calibration-id-input"
          />
        )}
        <button type="button" onClick={undo} disabled={points.length === 0}>
          마지막 점 취소
        </button>
        <button type="button" onClick={reset} disabled={points.length === 0}>
          전체 초기화
        </button>
        <button type="button" onClick={copyPoints} disabled={points.length === 0}>
          px 좌표 복사
        </button>
      </div>
      {src ? (
        <div className="calibration-image-wrap">
          <img
            ref={imgRef}
            src={src}
            alt={`${title} 대상 이미지`}
            className="calibration-image"
            onClick={handleImageClick}
          />
          {points.map((p, i) => (
            <span key={i} className="calibration-point" style={{ left: `${p.xPct}%`, top: `${p.yPct}%` }}>
              {i + 1}
            </span>
          ))}
        </div>
      ) : (
        <p className="calibration-missing">이 ID의 이미지를 찾을 수 없습니다.</p>
      )}
      {points.length > 0 && (
        <ol className="calibration-point-list">
          {points.map((p, i) => (
            <li key={i}>
              #{i + 1} — px ({p.xPx}, {p.yPx}) · {p.xPct.toFixed(2)}%, {p.yPct.toFixed(2)}%
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/** Debug-only coordinate picker, reachable via the `?calibrate=1` query
 * param (see `App.tsx`) — never linked to from in-game UI. Click a target
 * slot's corners on one panel and the source image's own meaningful corners
 * on the other, then read off natural-pixel coordinates directly instead of
 * eyeballing them in an external image editor. */
export function CalibrationView() {
  return (
    <div className="calibration-view">
      <header className="calibration-header">
        <h2>좌표 보정 도구</h2>
        <p>
          이미지를 클릭하면 그 지점의 원본 px 좌표와 %가 기록됩니다. 왼쪽엔 맞춰야 하는 칸(대상
          슬롯)을, 오른쪽엔 그 칸에 배치할 이미지를 띄워두고 대응되는 모서리를 순서대로 찍으세요.
        </p>
      </header>
      <div className="calibration-panels">
        <CalibrationPanel title="칸 (대상 슬롯)" />
        <CalibrationPanel title="이미지 (배치할 소스)" />
      </div>
    </div>
  );
}
