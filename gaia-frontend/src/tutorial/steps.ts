import type { GameEvent, PlayerId } from '../types/game';

/**
 * The guided first game. Rather than scripting a fake board, each step watches the real event log
 * the server already writes, so the engine stays the judge of whether an action was legal and the
 * learner plays an actual game while following along.
 */

export interface TutorialStep {
  id: string;
  title: string;
  /** What to do, in one imperative sentence. */
  instruction: string;
  /** Where to look when stuck. */
  hint: string;
  /** True for the event that proves this player did it. */
  matches: (event: GameEvent, me: PlayerId) => boolean;
}

function payload(event: GameEvent, tag: string): Record<string, unknown> | null {
  const record = event as Record<string, unknown>;
  const value = record[tag];
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/** Most steps are "this player produced this kind of event". */
function byTag(tag: string) {
  return (event: GameEvent, me: PlayerId) => payload(event, tag)?.player === me;
}

/** Power actions leave their resource changes in the log; the boundary marker names the action. */
function byActionLog(action: string) {
  return (event: GameEvent, me: PlayerId) => {
    const marker = payload(event, 'ActionLog');
    return marker?.player === me && marker?.action === action;
  };
}

export const TUTORIAL_STEPS: TutorialStep[] = [
  {
    id: 'build',
    title: '광산 짓기',
    instruction: '노란 테두리가 뜬 행성 하나를 골라 광산을 지어보세요.',
    hint: '위쪽 "우주" 바로가기로 지도를 열고, 지을 수 있는 행성을 누르면 비용이 먼저 표시됩니다.',
    matches: byTag('StructureBuilt'),
  },
  {
    id: 'free-action',
    title: '자원 바꿔보기',
    instruction: '자유 행동으로 자원을 한 번 교환해보세요. 차례는 넘어가지 않습니다.',
    hint: '오른쪽 정보 탭 아래 자유 행동 목록에서 "파워 1 → 크레딧 1" 같은 것을 눌러보세요.',
    matches: byTag('FreeActionTaken'),
  },
  {
    id: 'research',
    title: '연구 올리기',
    instruction: '지식 4를 써서 연구 트랙을 한 칸 올려보세요.',
    hint: '"연구·함선" 바로가기 → 연구판에서 원하는 트랙의 내 표식을 누릅니다.',
    matches: byTag('ResearchAdvanced'),
  },
  {
    id: 'upgrade',
    title: '건물 키우기',
    instruction: '광산 하나를 교역소로 업그레이드해보세요.',
    hint: '지도에서 내 광산을 누르면 업그레이드 선택지가 나옵니다. 상대 건물 옆이면 크레딧이 절반입니다.',
    matches: byTag('StructureUpgraded'),
  },
  {
    id: 'power-action',
    title: '공용 파워 행동 써보기',
    instruction: '연구판 아래 공용 칸에서 파워를 자원으로 바꿔보세요.',
    hint: '한 칸은 라운드당 한 사람만 씁니다. 원하는 칸이 있으면 먼저 잡는 편이 좋습니다.',
    matches: byActionLog('PowerAction'),
  },
  {
    id: 'gaia',
    title: '가이아 프로젝트 걸기',
    instruction: '차원변형행성에 가이아 프로젝트를 시작해보세요.',
    hint: '가이아 프로젝트 연구가 1단계 이상이어야 합니다. 다음 라운드에 행성이 바뀝니다.',
    matches: byTag('GaiaFormingStarted'),
  },
  {
    id: 'federation',
    title: '연방 만들기',
    instruction: '건물들을 이어 파워 값 7 이상으로 연방을 만들어보세요.',
    hint: '떨어진 건물은 위성으로 잇습니다. 위성 하나당 파워 토큰 1개를 버립니다.',
    matches: byTag('FederationFormed'),
  },
  {
    id: 'pass',
    title: '패스하고 부스터 고르기',
    instruction: '이번 라운드를 마치고 다음 라운드에 쓸 부스터를 고르세요.',
    hint: '먼저 패스하면 다음 라운드 선 순서를 가져갑니다.',
    matches: byTag('PlayerPassed'),
  },
];

export interface TutorialProgress {
  doneIds: string[];
  /** The step to show now, or `null` once every step is done. */
  current: TutorialStep | null;
  completed: boolean;
}

/**
 * Steps are checked off independently: a learner who forms a federation before upgrading has still
 * done both, and nothing should tell them otherwise. The step shown next is simply the first one
 * still outstanding.
 */
export function tutorialProgress(
  events: GameEvent[] | undefined,
  me: PlayerId | null,
  steps: TutorialStep[] = TUTORIAL_STEPS,
): TutorialProgress {
  const log = events ?? [];
  const doneIds = me === null
    ? []
    : steps.filter((step) => log.some((event) => step.matches(event, me))).map((step) => step.id);
  const current = steps.find((step) => !doneIds.includes(step.id)) ?? null;
  return { doneIds, current, completed: current === null && steps.length > 0 };
}
