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

import { explorationBoardImageSrc } from '../../assets/explorationBoardImages';
import { roundBoosterImageSrc } from '../../assets/roundBoosterImages';
import { tinkeringTileImageSrc } from '../../assets/tinkeringTileImages';
import { factionDisplayName, spaceshipDisplayName } from '../../displayNames';
import { SPACESHIP_ACTION_SPACES, POWER_ACTION_SPACES } from '../boardActionSpaces';

const QIC_OVERLAY_SRC = qicOverlayImageSrc;

type AssetCategory =
  | 'actionSource'
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

// Stable keys accompany coordinates so repeated crops from one board remain distinguishable.
const ACTION_SOURCES = [
  { id: 'standard-10', label: '일반 기술 10 · 파워 4 충전', src: standardTechTileImageSrc(10) },
  ...[[20, '지식 3'], [21, '광석 3'], [22, '정보 큐브 1 + 크레딧 5']].map(([id, effect]) => ({
    id: `advanced-${id}`, label: `고급 기술 ${id} · ${effect}`, src: advancedTechTileImageSrc(Number(id)),
  })),
  { id: 'booster-5', label: '부스터 5 · 즉시 가이아포밍', src: roundBoosterImageSrc(5) },
  { id: 'booster-8', label: '부스터 8 · 사거리 +3', src: roundBoosterImageSrc(8) },
  ...['테라포밍 1단계 무료 광산', '정보 큐브 1', '파워 4 충전', '정보 큐브 2', '테라포밍 3단계 무료 광산', '지식 3'].map((effect, index) => ({
    id: `tinkering-${index + 1}`,
    label: `팅커로이드 타일 ${index + 1} · ${index < 3 ? '1~3' : '4~6'}라운드 · ${effect}`,
    src: tinkeringTileImageSrc(index + 1),
  })),
  ...SHIP_IDS.flatMap((ship) => SPACESHIP_ACTION_SPACES[ship].map((action) => ({
    id: `ship-${ship}-${action.id}`,
    label: `${spaceshipDisplayName(ship)} · ${action.label}`,
    src: spaceshipBoardImageSrc(ship),
  }))),
  ...POWER_ACTION_SPACES.map((action) => ({
    id: `power-${action.id}`, label: `연구 보드 · ${action.label}`, src: researchBoardImageSrc(),
  })),
  { id: 'exploration-SpaceGiants-build-mine', label: '스페이스자이언트 · 확장 보드 행동 · 광산 건설 (테라포밍 2단계 무료)', src: explorationBoardImageSrc('SpaceGiants') },
  { id: 'exploration-Xenos-ore-to-power', label: '제노스 · 확장 보드 자유 행동 · 광석 1 → III구역 파워 토큰 1', src: explorationBoardImageSrc('Xenos') },
  { id: 'exploration-Gleens-range', label: '글린 · 확장 보드 행동 · 사거리 +2 (광산·가이아 프로젝트·함선 탐사)', src: explorationBoardImageSrc('Gleens') },
  { id: 'faction-BalTaks-credit-academy', label: '발타크 · 크레딧 아카데미 행동', src: factionBoardImageSrc('BalTaks') },
  { id: 'faction-Geodens-credit-academy', label: '기오덴 · 크레딧 아카데미 행동', src: factionBoardImageSrc('Geodens') },
  { id: 'faction-Firaks-downgrade', label: '파이락 · 의회 능력 · 연구소 강등 + 무료 연구', src: factionBoardImageSrc('Firaks') },
  { id: 'faction-Ivits-space-station', label: '하이브 · 의회 능력 · 우주정거장 배치', src: factionBoardImageSrc('Ivits') },
  { id: 'faction-Moweyds-power-ring', label: '모웨이드 · 의회 능력 · 파워 링 설치', src: factionBoardImageSrc('Moweyds') },
  { id: 'faction-Bescods-research', label: '매드안드로이드 · 최저 연구 트랙 올리기', src: factionBoardImageSrc('Bescods') },
  ...FACTION_IDS.flatMap((faction) => [
    { id: `faction-${faction}`, label: `${factionDisplayName(faction)} · 기본 종족 보드 (능력·아카데미)`, src: factionBoardImageSrc(faction) },
    { id: `exploration-${faction}`, label: `${factionDisplayName(faction)} · 확장 종족 보드`, src: explorationBoardImageSrc(faction) },
  ]),
].filter((asset) => !!asset.src);

const CATEGORY_LABEL: Record<AssetCategory, string> = {
  actionSource: '액션 부분 매핑용 이미지 모음',
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
  lostFleetTechRequirement: '고급 기술 조건 보드 (승점 25/탐사선 3개, 잃어버린 함대 뒷면)',
  economyOverlay: '경제 연구 3·4레벨 대체 타일 (연구판 오버레이)',
  qicOverlay: '잃어버린 함대 정보 큐브 액션칸 폐쇄 오버레이 (연구판 오버레이)',
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
    case 'actionSource':
      return ACTION_SOURCES.find((asset) => asset.id === id)?.src ?? undefined;
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
  if (category === 'actionSource') return ACTION_SOURCES[0].id;
  if (category === 'shipBoard') return SHIP_IDS[0];
  if (category === 'factionBoard') return FACTION_IDS[0];
  if (category === 'economyOverlay') return ECONOMY_SIDES[0];
  for (let id = 1; id <= 30; id += 1) {
    if (resolveSrc(category, String(id))) return String(id);
  }
  return '1';
}

function CalibrationPanel({ title, moweyds = false }: { title: string; moweyds?: boolean }) {
  const [category, setCategory] = useState<AssetCategory>('actionSource');
  const [idInput, setIdInput] = useState<string>(moweyds ? 'faction-Moweyds-power-ring' : ACTION_SOURCES[0].id);
  const [zoom, setZoom] = useState(moweyds ? 1 : 0);
  const [points, setPoints] = useState<Point[]>([]);
  const imgRef = useRef<HTMLImageElement>(null);

  const src = resolveSrc(category, idInput);
  const assetLabel = category === 'actionSource'
    ? ACTION_SOURCES.find((asset) => asset.id === idInput)?.label ?? idInput
    : `${CATEGORY_LABEL[category]} · ${category === 'shipBoard' ? spaceshipDisplayName(idInput as SpaceshipId) : category === 'factionBoard' ? factionDisplayName(idInput as FactionId) : idInput}`;

  function handleCategoryChange(next: AssetCategory) {
    setCategory(next);
    setIdInput(firstValidId(next));
    setPoints([]);
    setZoom(0);
  }

  function handleIdChange(next: string) {
    setIdInput(next);
    setPoints([]);
    setZoom(0);
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
    const coordinates = points.map((p) => `${p.xPx}, ${p.yPx}`).join('\n');
    const text = category === 'actionSource'
      ? `${assetLabel} [${idInput}]\n원본: ${imgRef.current?.naturalWidth} × ${imgRef.current?.naturalHeight}\n${coordinates}`
      : coordinates;
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
        {category === 'actionSource' ? (
          <select aria-label={`${title} 액션 이미지`} value={idInput} onChange={(e) => handleIdChange(e.target.value)}>
            {ACTION_SOURCES.map((asset) => (
              <option key={asset.id} value={asset.id}>{asset.label}</option>
            ))}
          </select>
        ) : category === 'shipBoard' ? (
          <select value={idInput} onChange={(e) => handleIdChange(e.target.value)}>
            {SHIP_IDS.map((id) => (
              <option key={id} value={id}>
                {spaceshipDisplayName(id)}
              </option>
            ))}
          </select>
        ) : category === 'factionBoard' ? (
          <select value={idInput} onChange={(e) => handleIdChange(e.target.value)}>
            {FACTION_IDS.map((id) => (
              <option key={id} value={id}>
                {factionDisplayName(id)}
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
      <h4>{assetLabel}</h4>
      {src === factionBoardImageSrc('Moweyds') && (
        <label>모웨이드 보드 확대{' '}
          <select aria-label="모웨이드 보드 확대" value={zoom} onChange={(e) => setZoom(Number(e.target.value))}>
            <option value={0}>화면에 맞춤</option>
            <option value={1}>원본 크기 (100%)</option>
            <option value={2}>크게 (200%)</option>
          </select>
          <span> 확대해도 복사되는 좌표는 원본 기준입니다. 이미지 영역을 스크롤해 이동하세요.</span>
        </label>
      )}
      {category === 'actionSource' && (
        <p>남길 액션 그림의 외곽 모서리를 순서대로 찍어 주세요. 좌표 복사에 이미지 이름과 ID도 함께 포함됩니다.</p>
      )}
      {src ? (
        <div className="calibration-image-scroll">
        <div className="calibration-image-wrap" style={zoom ? { width: 2323 * zoom, maxWidth: 'none' } : undefined}>
          <img
            ref={imgRef}
            src={src}
            alt={assetLabel}
            className="calibration-image"
            style={zoom ? { width: '100%', maxWidth: 'none', border: 0 } : undefined}
            onClick={handleImageClick}
          />
          {points.map((p, i) => (
            <span key={i} className="calibration-point" style={{ left: `${p.xPct}%`, top: `${p.yPct}%` }}>
              {i + 1}
            </span>
          ))}
        </div>
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
  const moweyds = new URLSearchParams(window.location.search).get('asset') === 'Moweyds';
  return (
    <div className="calibration-view">
      <header className="calibration-header">
        <h2>좌표 보정 도구</h2>
        <p>
          이미지를 클릭하면 그 지점의 원본 px 좌표와 %가 기록됩니다. 왼쪽엔 맞춰야 하는 칸(대상
          슬롯)을, 오른쪽엔 그 칸에 배치할 이미지를 띄워두고 대응되는 모서리를 순서대로 찍으세요.
        </p>
      </header>
      <div className="calibration-panels" style={moweyds ? { gridTemplateColumns: 'minmax(0, 1fr)' } : undefined}>
        {!moweyds && <CalibrationPanel title="칸 (대상 슬롯)" />}
        <CalibrationPanel title="이미지 (배치할 소스)" moweyds={moweyds} />
      </div>
    </div>
  );
}
