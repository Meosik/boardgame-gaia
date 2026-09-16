import { useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import {
  FACTION_STRUCTURE_COLOR,
  STRUCTURE_COLOR_HEX,
} from '../../assets/structureImages';
import type { BoardState, FreeActionKind, GameEvent, PlayerId, PlayerState } from '../../types/game';
import { hexLocationLabel } from '../../hexLocation';
import { FACTION_DISPLAY_NAMES, SPACESHIP_DISPLAY_NAMES } from '../../displayNames';
import { ACTION_NAMES as REPLAY_ACTION_NAMES } from '../../replay/records';

interface Props {
  events: GameEvent[];
  players: PlayerState[];
  /** Turns coordinates in the log into board positions ("3번 섹터 화산 행성"). */
  board?: BoardState | null;
  onEventSelect?: (eventIndex: number) => void;
  activeEventRange?: [number, number];
}

type EventPayload = Record<string, unknown>;

const FREE_ACTION_LABELS: Record<FreeActionKind, string> = {
  BurnPower: '파워 희생', CreditsToQic: '크레딧 → 정보 큐브', CreditsToOre: '크레딧 → 광석',
  CreditsToKnowledge: '크레딧 → 지식', GaiaformerToQic: '가이아포머 → 정보 큐브',
  PowerToGaiaKnowledge: '파워 → 가이아 영역 + 지식', OreToPowerBowl3: '광석 → 3단계 파워',
  PowerToQic: '파워 → 정보 큐브', PowerToOre: '파워 → 광석', QicToOre: '정보 큐브 → 광석',
  PowerToKnowledge: '파워 → 지식', PowerToCredit: '파워 → 크레딧',
  KnowledgeToCredit: '지식 → 크레딧', OreToCredit: '광석 → 크레딧', OreToPower: '광석 → 파워 토큰',
};

const TRACK_LABELS: Record<string, string> = {
  Terraforming: '테라포밍', Navigation: '항법', ArtificialIntelligence: '인공지능',
  GaiaProject: '가이아 프로젝트', Economy: '경제', Science: '과학',
};

const STRUCTURE_LABELS: Record<string, string> = {
  Mine: '광산', TradingStation: '교역소', ResearchLab: '연구소',
  PlanetaryInstitute: '행성의회', Satellite: '위성', SpaceStation: '우주 정거장',
};

function asRecord(value: unknown): EventPayload | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as EventPayload
    : null;
}

function payloadFor(event: GameEvent, tag: string): EventPayload | null {
  return asRecord(asRecord(event)?.[tag]);
}

function playerName(players: PlayerState[], player: unknown): string {
  const id = typeof player === 'number' ? player as PlayerId : -1;
  return players.find((candidate) => candidate.player_id === id)?.nickname ?? `플레이어 ${id}`;
}

function factionName(value: unknown): string {
  if (typeof value !== 'string') return '종족 미정';
  return FACTION_DISPLAY_NAMES[value as keyof typeof FACTION_DISPLAY_NAMES] ?? value;
}

function spaceshipName(value: unknown): string {
  const names = [
    SPACESHIP_DISPLAY_NAMES.Twilight,
    SPACESHIP_DISPLAY_NAMES.Rebellion,
    SPACESHIP_DISPLAY_NAMES.TFMars,
    SPACESHIP_DISPLAY_NAMES.Eclipse,
  ];
  return typeof value === 'number' ? names[value] ?? `함선 ${value}` : String(value);
}

function structureLabel(value: unknown): string {
  if (typeof value === 'string') return STRUCTURE_LABELS[value] ?? value;
  const academy = asRecord(value)?.Academy;
  return typeof academy === 'string' ? `아카데미(${academy === 'Qic' ? '정보 큐브' : '과학'})` : '구조물';
}

function valueId(value: unknown): string {
  if (typeof value === 'number' || typeof value === 'string') return String(value);
  const record = asRecord(value);
  if (!record) return '?';
  const first = Object.values(record)[0];
  return typeof first === 'number' || typeof first === 'string' ? String(first) : '?';
}

/** Board position in the words on the table ("3번 섹터 화산 행성"); the raw axial coordinate is the
 * fallback for snapshots rendered without a board. */
function hexLabel(value: unknown, board?: BoardState | null): string {
  if (typeof value === 'string') {
    const [q, r] = value.split(',').map(Number);
    return Number.isFinite(q) && Number.isFinite(r) ? hexLocationLabel({ q, r }, board) : `(${value})`;
  }
  const hex = asRecord(value);
  return hex && typeof hex.q === 'number' && typeof hex.r === 'number'
    ? hexLocationLabel({ q: hex.q, r: hex.r }, board)
    : '(?)';
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function renderLogText(text: string, players: PlayerState[]): ReactNode {
  const playersByName = new Map(players.map((player) => [player.nickname, player]));
  const names = [...playersByName.keys()].filter(Boolean).sort((left, right) => right.length - left.length);
  if (names.length === 0) return text;
  const namePattern = new RegExp(`(${names.map(escapeRegExp).join('|')})`, 'g');

  return text.split(namePattern).map((part, index) => {
    const player = playersByName.get(part);
    if (!player) return part;
    const color = player.faction
      ? STRUCTURE_COLOR_HEX[FACTION_STRUCTURE_COLOR[player.faction]]
      : '#cbd5e1';
    return (
      <strong
        key={`${part}-${index}`}
        className="game-log-player-name"
        style={{ '--log-player-color': color } as CSSProperties}
      >
        {part}
      </strong>
    );
  });
}

function vpReason(value: unknown): string {
  if (typeof value === 'string') {
    const labels: Record<string, string> = {
      ResourceConversion: '자원 변환', FactionSpecial: '종족 능력', GaiaProject: '가이아 프로젝트',
      ShipExploration: '함선 탐사', AsteroidColony: '소행성 식민지', ProtoPlanetColony: '원시 행성 식민지',
      QicAction: 'QIC 행동',
    };
    return labels[value] ?? value;
  }
  const reason = asRecord(value);
  if (!reason) return '점수 효과';
  if ('FederationToken' in reason) return `연방 토큰 #${String(asRecord(reason.FederationToken)?.token_kind)} 효과`;
  if ('TechTile' in reason) return `기술 타일 #${valueId(reason.TechTile)}`;
  if ('RoundTile' in reason) return `라운드 타일 #${valueId(reason.RoundTile)}`;
  if ('FinalTile' in reason) return `게임 종료 타일 #${valueId(reason.FinalTile)}`;
  if ('RoundBooster' in reason) return `라운드 부스터 #${valueId(reason.RoundBooster)}`;
  if ('ResearchTrack' in reason) {
    const track = asRecord(reason.ResearchTrack)?.track;
    return `연구 ${TRACK_LABELS[String(track)] ?? String(track)}`;
  }
  return '점수 효과';
}

function formatEvent(event: GameEvent, players: PlayerState[], board?: BoardState | null): string | null {
  let payload = payloadFor(event, 'ReplayDecision');
  if (payload) {
    const action = asRecord(payload.action) ?? {};
    const type = String(action.type);
    const details = [
      action.coord != null ? hexLabel(action.coord, board) : '',
      action.to != null ? structureLabel(action.to) : '',
      action.track != null ? TRACK_LABELS[String(action.track)] ?? String(action.track) : '',
      action.ship != null ? SPACESHIP_DISPLAY_NAMES[action.ship as keyof typeof SPACESHIP_DISPLAY_NAMES] ?? String(action.ship) : '',
      action.kind != null && type === 'FreeAction' ? `${FREE_ACTION_LABELS[action.kind as FreeActionKind] ?? action.kind} ×${String(action.count)}` : '',
      action.booster_id != null ? `부스터 #${String(action.booster_id)}` : '',
      action.accept != null ? action.accept ? '수락' : '거절' : '',
      action.id != null ? `#${String(action.id)}` : '',
      action.artifact != null ? `아티팩트 #${String(action.artifact)}` : '',
    ].filter(Boolean);
    return `#${String(payload.step)} · ${String(payload.round)}R ${playerName(players, payload.player)}: ${REPLAY_ACTION_NAMES[type] ?? ACTION_LABELS[type] ?? type}${details.length ? ` · ${details.join(' · ')}` : ''}`;
  }
  payload = payloadFor(event, 'FactionSelected');
  if (payload) return `${playerName(players, payload.player)}: 종족 ${factionName(payload.faction)} 선택`;
  payload = payloadFor(event, 'BidPlaced');
  if (payload) return `${playerName(players, payload.player)}: 승점 ${String(payload.amount)}점 입찰`;
  payload = payloadFor(event, 'BidPassed');
  if (payload) return `${playerName(players, payload.player)}: 입찰 패스`;
  payload = payloadFor(event, 'BidWon');
  if (payload) return `${playerName(players, payload.player)}: 승점 ${String(payload.amount)}점으로 ${factionName(payload.faction)}·${String(payload.turn_position)}번 순서 획득`;

  payload = payloadFor(event, 'FreeActionTaken');
  if (payload) {
    const kind = String(payload.kind) as FreeActionKind;
    return `${playerName(players, payload.player)}: ${FREE_ACTION_LABELS[kind] ?? kind} ×${String(payload.count)}`;
  }
  payload = payloadFor(event, 'ResourceChanged');
  if (payload) {
    const delta = asRecord(payload.delta) ?? {};
    const labels: [string, string][] = [['ore', '광석'], ['credits', '크레딧'], ['knowledge', '지식'], ['qic', '정보 큐브']];
    const changes = labels.flatMap(([key, label]) => {
      const amount = delta[key];
      return typeof amount === 'number' && amount !== 0 ? [`${label} ${amount > 0 ? '+' : ''}${amount}`] : [];
    });
    return `${playerName(players, payload.player)}: 자원 변화 ${changes.join(', ') || '없음'}`;
  }
  payload = payloadFor(event, 'IncomeReceived');
  if (payload) {
    const income = payload;
    const labels: [string, string][] = [
      ['ore', '광석'], ['credits', '크레딧'], ['knowledge', '지식'], ['qic', '정보 큐브'],
    ];
    const gains = labels.flatMap(([key, label]) => {
      const amount = income[key];
      return typeof amount === 'number' && amount > 0 ? [`${label} +${amount}`] : [];
    });
    if (typeof income.power_charge === 'number' && income.power_charge > 0) {
      gains.push(`파워 충전 +${income.power_charge}`);
    }
    if (typeof income.power_tokens === 'number' && income.power_tokens > 0) {
      gains.push(`파워 토큰 +${income.power_tokens}`);
    }
    if (typeof income.vp === 'number' && income.vp > 0) gains.push(`승점 +${income.vp}점`);
    return `${playerName(players, income.player)}: ${String(income.round)}라운드 수입 ${gains.join(', ') || '없음'}`;
  }
  payload = payloadFor(event, 'ReplaySettlement');
  if (payload) {
    const amount = Number(payload.amount);
    return `정산 · ${String(payload.title)} · ${playerName(players, payload.player)}: ${String(payload.detail)} · 승점 ${amount > 0 ? '+' : ''}${amount}점 · 누적 ${String(payload.total)}점`;
  }
  payload = payloadFor(event, 'VpAwarded');
  if (payload) {
    const particle = payload.reason === 'QicAction' ? '으로' : '로';
    return `${playerName(players, payload.player)}: ${vpReason(payload.reason)}${particle} 승점 ${String(payload.amount)}점`;
  }

  payload = payloadFor(event, 'StructureBuilt');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)}에 ${structureLabel(payload.kind)} 건설`;
  payload = payloadFor(event, 'StructureUpgraded');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)} ${structureLabel(payload.from)} → ${structureLabel(payload.to)}`;
  payload = payloadFor(event, 'StructuresSwapped');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.first, board)}와 ${hexLabel(payload.second, board)}의 행성의회·광산 교환`;
  payload = payloadFor(event, 'FederationFormed');
  if (payload) return `${playerName(players, payload.player)}: 연방 형성 (토큰 #${valueId(payload.token)})`;
  payload = payloadFor(event, 'ResearchAdvanced');
  if (payload) return `${playerName(players, payload.player)}: ${TRACK_LABELS[String(payload.track)] ?? String(payload.track)} 연구 ${String(payload.level)}단계`;
  payload = payloadFor(event, 'LostPlanetPlaced');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)}에 검은 행성 배치`;
  payload = payloadFor(event, 'GaiaFormingStarted');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)} 가이아포밍 시작`;
  payload = payloadFor(event, 'GaiaFormingComplete');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)} 가이아포밍 완료`;
  payload = payloadFor(event, 'BoosterSelected');
  if (payload) return `${playerName(players, payload.player)}: 초기 부스터 #${valueId(payload.booster)} 선택`;
  payload = payloadFor(event, 'PlayerPassed');
  if (payload) return `${playerName(players, payload.player)}: 패스${valueId(payload.booster) === '0' ? '' : ` (부스터 #${valueId(payload.booster)} 반납)`}`;

  payload = payloadFor(event, 'UndoRequested');
  if (payload) return `${playerName(players, payload.requester)}: 직전 차례 되돌리기 요청`;
  payload = payloadFor(event, 'UndoRejected');
  if (payload) return `${playerName(players, payload.responder)}: ${playerName(players, payload.requester)}님의 되돌리기 거절`;
  payload = payloadFor(event, 'UndoApplied');
  if (payload) return `${playerName(players, payload.requester)}: ${payload.free_action_only ? '이번 차례 자유행동 전부' : '직전 차례'} 되돌림`;

  payload = payloadFor(event, 'ShipExplored');
  if (payload) return `${playerName(players, payload.player)}: ${spaceshipName(payload.ship_id)} 함선 탐사`;
  payload = payloadFor(event, 'AsteroidColonized');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)} 소행성 식민지 건설`;
  payload = payloadFor(event, 'ProtoPlanetColonized');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex, board)} 원시 행성 식민지 건설`;
  payload = payloadFor(event, 'ArtifactExamined');
  if (payload) return `${playerName(players, payload.player)}: 아티팩트 #${valueId(payload.artifact)} 조사`;
  payload = payloadFor(event, 'TechTileGained');
  if (payload) return `${playerName(players, payload.player)}: 기술 타일 #${valueId(payload.tile)} 획득`;

  payload = payloadFor(event, 'RoundStarted');
  if (payload) return `${String(payload.round)}라운드 시작`;
  payload = payloadFor(event, 'RoundEnded');
  if (payload) return `${String(payload.round)}라운드 종료`;
  payload = payloadFor(event, 'GameEnded');
  if (payload) return `게임 종료 — 최종 점수 ${(Array.isArray(payload.final_scores) ? payload.final_scores : []).join(' / ')}`;
  return null;
}

interface LogEntry {
  index: number;
  /** Actor of the grouped action, for live UI that treats own and opponents' moves differently. */
  player: number | null;
  text: string;
  details: string[];
}

const DETAIL_TAGS = new Set(['ResourceChanged', 'VpAwarded']);
const COST_FIRST_TAGS = new Set(['ResearchAdvanced', 'StructureBuilt', 'StructureUpgraded', 'GaiaFormingStarted']);
const ACTION_LABELS: Record<string, string> = {
  PowerAction: '파워 행동', QicAction: 'QIC 행동', SpecialAction: '종족 행동',
  TinkeroidsUseTile: '팅커링 타일 행동', TechTileSpecialAction: '기술 타일 행동',
  AcademyQicAction: '정보 아카데미 행동', ChargePower: '파워 충전 선택',
  TaklonsChargePower: '파워 토큰 추가·충전', ChooseIncomeOrder: '수입 순서 선택',
  FinishGaiaDecision: '가이아 단계 완료', ItarsGaiaTechChoice: '가이아 기술 획득',
  ItarsGaiaTechTile: '가이아 기술 획득', TerransGaiaConversion: '가이아 파워 교환',
  RebellionCreditsAndQic: '리벨리온 자원 행동', TFMarsTechBonus: 'TF Mars 기술 점수 행동',
  EclipsePlanetTypeBonus: '이클립스 행성 종류 점수 행동',
  TwilightReplayFederationToken: '연방 토큰 효과 복사',
};

function eventTag(event: GameEvent): string {
  return Object.keys(event)[0] ?? '';
}

function eventPlayer(event: GameEvent): unknown {
  return payloadFor(event, eventTag(event))?.player;
}

function makeEntry(events: GameEvent[], index: number, players: PlayerState[], action?: EventPayload, board?: BoardState | null): LogEntry | null {
  const decision = payloadFor(events[0], 'ReplayDecision');
  if (decision) {
    const changes = Array.isArray(decision.net_changes) ? decision.net_changes : [];
    const labels: Record<string, string> = { ore: '광석', credits: '크레딧', knowledge: '지식', qic: '정보 큐브', vp: '승점' };
    const details = changes.flatMap(value => {
      const change = asRecord(value);
      const delta = asRecord(change?.delta);
      if (!change || !delta) return [];
      return [`${playerName(players, change.player)} 순변화: ${Object.entries(delta).map(([key, amount]) => `${labels[key] ?? key} ${Number(amount) > 0 ? '+' : ''}${String(amount)}`).join(', ')}`];
    });
    return { index, player: typeof decision.player === 'number' ? decision.player : null,
      text: formatEvent(events[0], players, board) ?? 'AI 행동', details: [
      '기록된 상태 간 순변화입니다. 자동 수입·라운드 전환·최종 정산이 포함될 수 있습니다.',
      ...details, `선택 데이터: ${JSON.stringify(decision.action)}`,
    ] };
  }
  const formatted = events.map(event => ({ event, text: formatEvent(event, players, board) }))
    .filter((item): item is { event: GameEvent; text: string } => item.text !== null);
  const primary = formatted.find(({ event }) => !DETAIL_TAGS.has(eventTag(event)));
  const fallback = action
    ? `${playerName(players, action.player)}: ${ACTION_LABELS[String(action.action)] ?? '행동 수행'}`
    : formatted[0]?.text;
  const text = primary?.text ?? fallback;
  if (!text) return null;
  const actor = action?.player ?? eventPlayer(primary?.event ?? events[0]);
  return { index, player: typeof actor === 'number' ? actor : null, text,
    details: formatted.filter(item => item !== primary && (primary || action)).map(item => item.text) };
}

// Old snapshots have no action boundaries. Only join recognizable adjacent patterns;
// orphan costs/rewards remain visible rather than being assigned to a different action.
function legacyEntries(events: GameEvent[], offset: number, players: PlayerState[], board?: BoardState | null): LogEntry[] {
  const result: LogEntry[] = [];
  for (let i = 0; i < events.length; i += 1) {
    const start = i;
    const batch = [events[i]];
    let primary = events[i];
    const next = events[i + 1];
    const delta = payloadFor(primary, 'ResourceChanged')?.delta;
    if (next && eventTag(primary) === 'ResourceChanged'
      && Object.values(asRecord(delta) ?? {}).some(value => typeof value === 'number' && value < 0)
      && COST_FIRST_TAGS.has(eventTag(next)) && eventPlayer(primary) === eventPlayer(next)) {
      primary = next;
      batch.push(next);
      i += 1;
    }
    if (!DETAIL_TAGS.has(eventTag(primary)) && formatEvent(primary, players, board) !== null) {
      const player = eventPlayer(primary);
      while (player !== undefined && i + 1 < events.length && eventPlayer(events[i + 1]) === player) {
        const following = events[i + 1];
        const tag = eventTag(following);
        const freeActionDelta = eventTag(primary) === 'FreeActionTaken' && batch.length === 1 && tag === 'ResourceChanged';
        if (tag !== 'VpAwarded' && !freeActionDelta) break;
        batch.push(following);
        i += 1;
      }
    }
    const entry = makeEntry(batch, offset + start, players, undefined, board);
    if (entry) result.push(entry);
  }
  return result;
}

function groupedEntries(events: GameEvent[], players: PlayerState[], unlimited = false, board?: BoardState | null): LogEntry[] {
  const entries: LogEntry[] = [];
  let pendingStart = 0;
  events.forEach((event, index) => {
    const marker = payloadFor(event, 'ActionLog');
    if (!marker) return;
    const count = marker.event_count;
    if (typeof count !== 'number' || !Number.isSafeInteger(count) || count < 0 || count > index - pendingStart) return;
    const start = index - count;
    entries.push(...legacyEntries(events.slice(pendingStart, start), pendingStart, players, board));
    const entry = makeEntry(events.slice(start, index), start, players, marker, board);
    if (entry) entries.push(entry);
    pendingStart = index + 1;
  });
  entries.push(...legacyEntries(events.slice(pendingStart), pendingStart, players, board));
  return unlimited ? entries : entries.slice(-30).reverse();
}

export type GameLogEntry = LogEntry;

/** Same grouping the log panel shows, in play order and unabridged, for the live activity UI
 * (toast, recent-action list) so both describe an action with one wording. */
export function gameLogEntries(
  events: GameEvent[],
  players: PlayerState[],
  board?: BoardState | null,
): GameLogEntry[] {
  return groupedEntries(events, players, true, board);
}

function LogRow({ entry, players, onEventSelect, active }: { entry: LogEntry; players: PlayerState[]; onEventSelect?: (index: number) => void; active?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const { text, details } = entry;
  const isScore = text.includes('승점') || text.startsWith('게임 종료');
  const isPhase = /라운드 (시작|종료)/.test(text) || text.startsWith('게임 종료');
  return (
    <li aria-label={text} aria-current={active ? 'step' : undefined} className={`${isScore ? 'game-log-entry--score' : ''}${isPhase ? ' game-log-entry--phase' : ''}`.trim() || undefined}>
      {onEventSelect && <button type="button" className="game-log-seek" aria-label={`${text} 시점으로 이동`}
        onClick={() => onEventSelect(entry.index)}>↪ 이 시점</button>}
      {details.length > 0 ? (
        <>
          <button type="button" className="game-log-summary" aria-label={text} aria-expanded={expanded} onClick={() => { setExpanded(!expanded); onEventSelect?.(entry.index); }}>
            <span>{renderLogText(text, players)}</span>
            <span className="game-log-toggle" aria-hidden>{expanded ? '▾' : '▸'}</span>
          </button>
          {expanded && <div className="game-log-details">{details.map((detail, index) => (
            <p key={index}>{renderLogText(detail, players)}</p>
          ))}</div>}
        </>
      ) : onEventSelect ? <button type="button" className="game-log-summary" onClick={() => onEventSelect(entry.index)}>{renderLogText(text, players)}</button> : renderLogText(text, players)}
    </li>
  );
}

export function GameLog({ events, players, board, onEventSelect, activeEventRange }: Props) {
  const logRef = useRef<HTMLElement>(null);
  const replay = !!onEventSelect;
  const [activeStart, activeEnd] = activeEventRange ?? [];
  const entries = groupedEntries(events, players, !!onEventSelect, board);

  useLayoutEffect(() => {
    if (!replay || activeStart === undefined || activeEnd === undefined) return;
    const row = logRef.current?.querySelector<HTMLElement>('li[aria-current="step"]');
    const panel = logRef.current?.closest<HTMLElement>('.game-sidebar-tab-panel--log');
    if (!row || !panel || panel.clientHeight === 0 || panel.scrollHeight <= panel.clientHeight) return;
    // Only move the log viewport, never the board/page followed by replay navigation.
    const rowBounds = row.getBoundingClientRect();
    const panelTop = panel.getBoundingClientRect().top + panel.clientTop;
    const panelBottom = panelTop + panel.clientHeight;
    const titleBottom = logRef.current?.querySelector('.game-log-title')?.getBoundingClientRect().bottom ?? panelTop;
    const visibleTop = Math.max(panelTop, titleBottom);
    if (rowBounds.top < visibleTop || rowBounds.height > panelBottom - visibleTop) {
      panel.scrollTop += rowBounds.top - visibleTop;
    } else if (rowBounds.bottom > panelBottom) {
      panel.scrollTop += rowBounds.bottom - panelBottom;
    }
  }, [replay, activeStart, activeEnd, events]);

  return (
    <section ref={logRef} className="game-log" aria-label="게임 로그">
      <h3 className="game-log-title">게임 로그</h3>
      {entries.length === 0 ? (
        <p className="game-log-empty">아직 기록된 행동이 없습니다.</p>
      ) : (
        <ol className="game-log-list">{entries.map(entry => (
          <LogRow key={`${entry.index}:${entry.text}`} entry={entry} players={players} onEventSelect={onEventSelect}
            active={activeEventRange !== undefined && entry.index >= activeEventRange[0] && entry.index < activeEventRange[1]} />
        ))}</ol>
      )}
    </section>
  );
}
