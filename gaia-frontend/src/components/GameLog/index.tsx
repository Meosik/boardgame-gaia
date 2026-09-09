import type { FreeActionKind, GameEvent, PlayerId, PlayerState } from '../../types/game';

interface Props {
  events: GameEvent[];
  players: PlayerState[];
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
  return players.find((candidate) => candidate.player_id === id)?.nickname ?? `Player ${id}`;
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

function hexLabel(value: unknown): string {
  if (typeof value === 'string') return `(${value})`;
  const hex = asRecord(value);
  return hex && typeof hex.q === 'number' && typeof hex.r === 'number' ? `(${hex.q},${hex.r})` : '(?)';
}

function vpReason(value: unknown): string {
  if (typeof value === 'string') {
    const labels: Record<string, string> = {
      ResourceConversion: '자원 변환', FactionSpecial: '종족 능력', GaiaProject: '가이아 프로젝트',
      ShipExploration: '함선 탐사', AsteroidColony: '소행성 식민지', ProtoPlanetColony: '원시행성 식민지',
    };
    return labels[value] ?? value;
  }
  const reason = asRecord(value);
  if (!reason) return '점수 효과';
  if ('RoundTile' in reason) return `라운드 타일 #${valueId(reason.RoundTile)}`;
  if ('FinalTile' in reason) return `게임 종료 타일 #${valueId(reason.FinalTile)}`;
  if ('RoundBooster' in reason) return `라운드 부스터 #${valueId(reason.RoundBooster)}`;
  if ('ResearchTrack' in reason) {
    const track = asRecord(reason.ResearchTrack)?.track;
    return `연구 ${TRACK_LABELS[String(track)] ?? String(track)}`;
  }
  return '점수 효과';
}

function formatEvent(event: GameEvent, players: PlayerState[]): string | null {
  let payload = payloadFor(event, 'FactionSelected');
  if (payload) return `${playerName(players, payload.player)}: 종족 ${String(payload.faction)} 선택`;
  payload = payloadFor(event, 'BidPlaced');
  if (payload) return `${playerName(players, payload.player)}: 승점 ${String(payload.amount)}점 입찰`;
  payload = payloadFor(event, 'BidPassed');
  if (payload) return `${playerName(players, payload.player)}: 입찰 패스`;
  payload = payloadFor(event, 'BidWon');
  if (payload) return `${playerName(players, payload.player)}: 승점 ${String(payload.amount)}점으로 ${String(payload.faction)}·${String(payload.turn_position)}번 순서 획득`;

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
  payload = payloadFor(event, 'VpAwarded');
  if (payload) return `${playerName(players, payload.player)}: ${vpReason(payload.reason)}로 승점 ${String(payload.amount)}점`;

  payload = payloadFor(event, 'StructureBuilt');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)}에 ${structureLabel(payload.kind)} 건설`;
  payload = payloadFor(event, 'StructureUpgraded');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)} ${structureLabel(payload.from)} → ${structureLabel(payload.to)}`;
  payload = payloadFor(event, 'StructuresSwapped');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.first)}와 ${hexLabel(payload.second)}의 행성의회·광산 교환`;
  payload = payloadFor(event, 'FederationFormed');
  if (payload) return `${playerName(players, payload.player)}: 연방 형성 (토큰 #${valueId(payload.token)})`;
  payload = payloadFor(event, 'ResearchAdvanced');
  if (payload) return `${playerName(players, payload.player)}: ${TRACK_LABELS[String(payload.track)] ?? String(payload.track)} 연구 ${String(payload.level)}단계`;
  payload = payloadFor(event, 'LostPlanetPlaced');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)}에 검은 행성 배치`;
  payload = payloadFor(event, 'GaiaFormingStarted');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)} 가이아포밍 시작`;
  payload = payloadFor(event, 'GaiaFormingComplete');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)} 가이아포밍 완료`;
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
  if (payload) return `${playerName(players, payload.player)}: 함선 ${String(payload.ship_id)} 탐사`;
  payload = payloadFor(event, 'AsteroidColonized');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)} 소행성 식민지 건설`;
  payload = payloadFor(event, 'ProtoPlanetColonized');
  if (payload) return `${playerName(players, payload.player)}: ${hexLabel(payload.hex)} 원시행성 식민지 건설`;
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

export function GameLog({ events, players }: Props) {
  const entries = events
    .map((event, index) => ({ index, text: formatEvent(event, players) }))
    .filter((entry): entry is { index: number; text: string } => entry.text !== null)
    .slice(-30)
    .reverse();
  return (
    <section className="game-log" aria-label="게임 로그">
      <h3 className="game-log-title">게임 로그</h3>
      {entries.length === 0 ? (
        <p className="game-log-empty">아직 기록된 행동이 없습니다.</p>
      ) : (
        <ol className="game-log-list">
          {entries.map(({ index, text }) => <li key={index}>{text}</li>)}
        </ol>
      )}
    </section>
  );
}
