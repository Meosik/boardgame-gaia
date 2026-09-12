import { FREE_ACTIONS } from '../components/freeActions';
import { POWER_ACTION_SPACES } from '../components/boardActionSpaces';

/**
 * Beginner reference content. Every number here is the one the engine actually enforces — costs
 * come from `gaia-engine/src/rules/engine.rs` and `rules/terraforming.rs`, so a rule change that
 * moves a cost should move this text with it. Free actions and power-action spaces are read from
 * the tables the game itself renders, rather than restated, so those two can never drift.
 */

export type GuideCategory = 'flow' | 'main' | 'free' | 'expansion';

export interface GuideEntry {
  id: string;
  category: GuideCategory;
  title: string;
  /** What it costs, in the resources the player counts on their board. */
  cost?: string;
  /** What has to be true before the action is offered at all. */
  requires?: string;
  summary: string;
  detail: string[];
  tip?: string;
}

export const GUIDE_CATEGORIES: { id: GuideCategory; label: string; blurb: string }[] = [
  { id: 'flow', label: '라운드 흐름', blurb: '한 라운드가 어떤 순서로 진행되는지' },
  { id: 'main', label: '주요 행동', blurb: '내 차례에 하나 고르는 행동들' },
  { id: 'free', label: '자유 행동 · 자원', blurb: '차례를 쓰지 않는 자원 교환과 파워 순환' },
  { id: 'expansion', label: '확장 (잃어버린 함대)', blurb: '함선, 아티팩트, 새 행성' },
];

const FLOW: GuideEntry[] = [
  {
    id: 'flow-overview',
    category: 'flow',
    title: '게임 전체 구조',
    summary: '6라운드를 치르고, 마지막에 점수가 가장 높은 사람이 이깁니다.',
    detail: [
      '한 라운드는 수입 → 가이아 → 행동 → 정산 순서로 진행됩니다.',
      '대부분의 시간은 행동 단계에서 씁니다. 여기서 순서대로 한 번에 하나씩 행동합니다.',
      '라운드마다 목표 타일이 하나 걸려 있어, 그 조건을 만족하면 추가 점수를 받습니다.',
      '6라운드가 끝나면 최종 점수 타일 2개와 연구 트랙, 자원이 점수로 환산됩니다.',
    ],
    tip: '초반에는 점수보다 수입(광석·크레딧·지식)을 늘리는 쪽이 대체로 유리합니다.',
  },
  {
    id: 'flow-income',
    category: 'flow',
    title: '1. 수입 단계',
    summary: '건물과 연구 트랙, 부스터에 적힌 만큼 자원을 받습니다.',
    detail: [
      '내가 지은 건물이 많을수록, 연구 트랙이 높을수록 더 많이 받습니다.',
      '광산은 광석, 교역소는 크레딧, 연구소는 지식, 아카데미는 지식을 줍니다.',
      '파워 충전이 수입에 포함되면 파워 토큰이 다음 단계로 올라갑니다.',
      '파워 토큰을 새로 받는 것과 충전을 함께 받는 경우, 순서를 직접 고릅니다.',
    ],
  },
  {
    id: 'flow-gaia',
    category: 'flow',
    title: '2. 가이아 단계',
    summary: '가이아 프로젝트를 걸어둔 차원변형행성이 가이아 행성으로 바뀝니다.',
    detail: [
      '가이아 영역에 넣어둔 파워 토큰이 1단계로 돌아옵니다(테란은 2단계).',
      '변환이 끝난 행성에는 이번 라운드부터 광산을 지을 수 있습니다.',
      '가이아포머는 회수되어 다시 쓸 수 있습니다.',
    ],
  },
  {
    id: 'flow-action',
    category: 'flow',
    title: '3. 행동 단계',
    summary: '차례가 오면 주요 행동을 하나 하고 다음 사람에게 넘깁니다.',
    detail: [
      '주요 행동은 한 번에 하나입니다. 하고 나면 차례가 넘어갑니다.',
      '자유 행동(자원 교환)은 차례를 쓰지 않으므로 주요 행동 전에 여러 번 할 수 있습니다.',
      '더 할 것이 없거나 아껴야 하면 패스합니다. 패스한 사람은 그 라운드에 다시 행동하지 않습니다.',
    ],
    tip: '남이 내 건물 옆에 지으면 파워를 받을 수 있습니다. 받을지 말지는 직접 선택합니다.',
  },
  {
    id: 'flow-pass',
    category: 'flow',
    title: '4. 패스와 부스터',
    summary: '패스하면서 다음 라운드에 쓸 부스터를 하나 가져옵니다.',
    detail: [
      '먼저 패스한 사람이 다음 라운드의 선 순서를 가져갑니다.',
      '가지고 있던 부스터는 반납하고, 남은 것 중 하나를 새로 고릅니다.',
      '부스터에 "패스할 때 ~점" 조건이 있으면 반납하는 순간 점수를 받습니다.',
    ],
    tip: '마지막 라운드에는 패스 점수가 큰 부스터가 특히 값어치 있습니다.',
  },
  {
    id: 'flow-scoring',
    category: 'flow',
    title: '5. 라운드 정산',
    summary: '모두 패스하면 라운드 목표 점수를 정산하고 다음 라운드로 넘어갑니다.',
    detail: [
      '라운드마다 한 번씩 쓰는 행동(파워 행동, 특수 행동)이 다시 열립니다.',
      '게임당 한 번인 행동은 다시 열리지 않습니다.',
    ],
  },
];

const MAIN: GuideEntry[] = [
  {
    id: 'action-build',
    category: 'main',
    title: '광산 건설',
    cost: '광석 1 + 크레딧 2 (+ 테라포밍 광석)',
    requires: '내 건물에서 사거리 안에 있는 빈 행성',
    summary: '새 행성에 광산을 지어 발판과 수입을 늘립니다.',
    detail: [
      '내 종족의 고향 행성 종류가 아니면 테라포밍이 필요합니다.',
      '테라포밍은 행성 고리에서 몇 칸 떨어졌는지로 단계가 정해집니다. 대지-산성-화산-사막-늪-티타늄-얼음 순서의 고리입니다.',
      '단계당 광석은 테라포밍 연구 수준에 따라 3 → 3 → 2 → 1 → 1 → 1개로 줄어듭니다.',
      '사거리는 항법 연구 수준에 따라 1 → 1 → 2 → 2 → 3 → 4입니다. 정보 큐브 1개를 쓰면 사거리가 2 늘어납니다.',
      '가이아 행성에 지을 때는 테라포밍 대신 정보 큐브 1개가 듭니다.',
    ],
    tip: '사거리가 모자라면 정보 큐브를 자동으로 최소한만 씁니다. 미리 쓸 필요는 없습니다.',
  },
  {
    id: 'action-upgrade',
    category: 'main',
    title: '건물 업그레이드',
    cost: '교역소 광석 2 + 크레딧 6 (상대 건물 옆이면 크레딧 3) · 연구소 광석 3 + 크레딧 5 · 행성의회 광석 4 + 크레딧 6 · 아카데미 광석 6 + 크레딧 6',
    requires: '이미 지어둔 건물',
    summary: '건물을 더 좋은 건물로 바꿔 수입과 능력을 얻습니다.',
    detail: [
      '광산 → 교역소 → 연구소 → 아카데미 순서로 올라갑니다. 교역소에서 행성의회로도 갈 수 있습니다.',
      '업그레이드할 때 기술 타일을 하나 가져올 수 있습니다.',
      '행성의회는 종족마다 다른 특수 능력을 열어 줍니다.',
      '아카데미는 2개, 연구소는 3개, 교역소는 4개까지 지을 수 있습니다.',
    ],
    tip: '상대 건물 옆의 광산을 교역소로 올리면 크레딧이 절반입니다. 이웃이 있는 쪽부터 올리면 이득입니다.',
  },
  {
    id: 'action-research',
    category: 'main',
    title: '연구 진전',
    cost: '지식 4',
    summary: '연구 트랙을 한 칸 올려 능력과 점수를 얻습니다.',
    detail: [
      '트랙은 테라포밍·항법·인공지능·가이아 프로젝트·경제·과학 6개입니다.',
      '2단계에서 3단계로 올라갈 때 파워 3을 충전합니다.',
      '5단계는 트랙마다 한 사람만 갈 수 있고, 연방 토큰 하나를 회색으로 뒤집어야 합니다.',
    ],
    tip: '지식은 모아두기 어렵습니다. 연구소를 지어 지식 수입을 만들어 두는 편이 낫습니다.',
  },
  {
    id: 'action-gaia',
    category: 'main',
    title: '가이아 프로젝트',
    cost: '파워 6 → 6 → 4 → 3 → 3 (가이아 연구 수준별) + 가이아포머 1',
    requires: '가이아 프로젝트 연구 1단계 이상, 사거리 안의 차원변형행성',
    summary: '차원변형행성을 예약해 두었다가 다음 라운드에 가이아 행성으로 바꿉니다.',
    detail: [
      '가이아포머를 올려두고, 파워 토큰을 가이아 영역으로 옮깁니다.',
      '다음 라운드 가이아 단계에 행성이 바뀌고 가이아포머가 돌아옵니다.',
      '바뀐 가이아 행성에는 정보 큐브 1개로 광산을 지을 수 있습니다.',
    ],
  },
  {
    id: 'action-federation',
    category: 'main',
    title: '연방 형성',
    cost: '위성 1개당 파워 1 (하이브는 정보 큐브 1)',
    requires: '이어붙인 건물들의 파워 값 합계 7 이상',
    summary: '건물들을 이어 연방을 만들고 토큰 하나를 받습니다.',
    detail: [
      '건물의 파워 값은 광산 1, 교역소 2, 연구소 2, 행성의회 3, 아카데미 3입니다.',
      '떨어진 건물은 위성으로 잇습니다. 위성은 파워 토큰을 하나씩 버려서 놓습니다.',
      '연방 토큰은 점수와 자원을 주고, 나중에 고급 기술이나 5단계 연구의 대가로 뒤집어 씁니다.',
      '필요 이상으로 크게 만들 수 없습니다. 하나라도 빼도 성립하면 거절됩니다.',
    ],
    tip: '이미 만든 연방 옆에 새로 지으면 그 연방이 저절로 커집니다. 다만 추가 토큰은 없습니다.',
  },
  {
    id: 'action-power',
    category: 'main',
    title: '공용 파워 행동',
    cost: '칸마다 다름 (아래 목록)',
    requires: '그 라운드에 아직 아무도 쓰지 않은 칸',
    summary: '연구판 아래 공용 칸에서 파워를 자원이나 건설로 바꿉니다.',
    detail: [
      ...POWER_ACTION_SPACES.map((space) => `${space.id}번 칸 — ${space.label}`),
      '한 칸은 라운드당 한 번만, 전체 플레이어를 통틀어 한 사람만 쓸 수 있습니다.',
    ],
    tip: '원하는 칸이 있으면 미루지 마세요. 먼저 쓴 사람이 임자입니다.',
  },
  {
    id: 'action-special',
    category: 'main',
    title: '특수 행동',
    requires: '기술 타일, 행성의회, 부스터 등 각 원천에 적힌 조건',
    summary: '타일이나 종족 능력에 붙은, 라운드당 한 번 쓰는 행동입니다.',
    detail: [
      '기술 타일과 고급 기술 타일 일부에 "행동" 표시가 있습니다.',
      '행성의회를 지으면 종족 고유의 특수 행동이 열립니다.',
      '부스터에도 특수 행동이 붙은 것이 있습니다.',
      '정보 아카데미를 지으면 정보 큐브 1개를 얻는 행동을 쓸 수 있습니다.',
    ],
    tip: '라운드당 한 번짜리는 안 쓰면 사라집니다. 패스 전에 남은 것이 있는지 확인하세요.',
  },
];

const FREE: GuideEntry[] = [
  {
    id: 'free-power-cycle',
    category: 'free',
    title: '파워 순환 이해하기',
    summary: '파워는 1 → 2 → 3단계로 돌면서 3단계에서만 쓸 수 있습니다.',
    detail: [
      '충전은 토큰을 다음 단계로 옮기는 것입니다. 새로 얻는 것이 아닙니다.',
      '3단계 토큰을 쓰면 그 토큰은 1단계로 돌아갑니다.',
      '1단계에 토큰이 많을수록 충전이 잘 돌아갑니다. 토큰 자체를 늘리는 것도 방법입니다.',
      '파워 희생: 2단계 토큰 2개를 버리면 3단계 토큰 1개를 만듭니다. 급할 때 씁니다.',
    ],
    tip: '상대가 내 건물 옆에 지으면 충전 기회가 옵니다. 승점을 내고서라도 받을 만한지 그때그때 판단하세요.',
  },
  {
    id: 'free-conversions',
    category: 'free',
    title: '자유 행동 (자원 교환)',
    cost: '아래 목록',
    summary: '차례를 쓰지 않고 자원을 바꿉니다. 횟수 제한이 없습니다.',
    detail: [
      ...FREE_ACTIONS.filter((option) => !option.faction).map((option) => option.label),
      '종족 전용 교환은 해당 종족일 때만 보입니다(하드쉬 할라, 발 타크, 네블라, 제노스).',
    ],
    tip: '주요 행동을 하기 전에 필요한 자원을 먼저 만들어 두세요. 행동 후에는 차례가 넘어갑니다.',
  },
  {
    id: 'free-resources',
    category: 'free',
    title: '자원의 쓰임',
    summary: '광석은 건설, 크레딧은 업그레이드, 지식은 연구, 정보 큐브는 사거리와 특수 용도입니다.',
    detail: [
      '광석: 광산 건설과 테라포밍. 15개까지만 보관됩니다.',
      '크레딧: 업그레이드에 가장 많이 듭니다. 30까지 보관됩니다.',
      '지식: 연구 진전(4개). 15까지 보관됩니다. 모으기 가장 어렵습니다.',
      '정보 큐브: 사거리 연장, 가이아 행성 건설, 고급 기술 조건 등에 씁니다.',
    ],
  },
];

const EXPANSION: GuideEntry[] = [
  {
    id: 'lf-explore',
    category: 'expansion',
    title: '함선 탐사',
    cost: '승점 5 (+ 두 번째부터는 파워 충전 발생)',
    requires: '사거리 안의 함선 타일, 남은 탐사 셔틀',
    summary: '잃어버린 함대의 함선에 셔틀을 보내 그 함선의 행동칸과 보상을 엽니다.',
    detail: [
      '함선은 트와일라잇·리벨리온·T F 마스·이클립스 4척입니다.',
      '셔틀을 놓으면 그 함선에 붙은 행동칸을 쓸 수 있게 됩니다.',
      '먼저 탐사한 사람이 있으면, 뒤에 오는 사람은 칸 위치에 따라 파워를 충전받습니다.',
      '연방을 만들 때 그 함선에 남은 연방 토큰을 가져올 수도 있습니다.',
    ],
    tip: '승점 5는 비싸 보이지만, 함선 행동칸과 토큰까지 계산하면 초·중반에 회수되는 편입니다.',
  },
  {
    id: 'lf-artifact',
    category: 'expansion',
    title: '아티팩트 조사',
    cost: '파워 6 (버림)',
    requires: '트와일라잇에 놓은 셔틀',
    summary: '트와일라잇 함선에서 아티팩트 하나를 가져옵니다.',
    detail: [
      '아티팩트는 13종이고, 앞면이 보이므로 원하는 것을 골라 가져옵니다.',
      '즉시 점수, 즉시 자원, 매 라운드 수입 등 효과가 제각각입니다.',
      '연방 토큰 효과를 복사하는 것, 지도에 놓지 않는 가상 광산을 주는 것도 있습니다.',
    ],
  },
  {
    id: 'lf-planets',
    category: 'expansion',
    title: '새 행성 · 인터스페이스 칸',
    summary: '확장에는 소행성과 원시행성, 그리고 판 사이의 한 칸짜리 타일이 있습니다.',
    detail: [
      '원시행성: 테라포밍 3단계가 들지만 지으면 6점을 받습니다.',
      '소행성: 가이아포머 하나를 영구히 소모하는 대신 광산 비용이 들지 않습니다.',
      '인터스페이스 칸은 판과 판 사이의 한 칸입니다. 함선 타일도 이 자리에 놓입니다.',
      '위성은 함선 타일 위에 놓을 수 없습니다.',
    ],
  },
];

export const GUIDE_ENTRIES: GuideEntry[] = [...FLOW, ...MAIN, ...FREE, ...EXPANSION];

/** Case-insensitive search across every field a player might type a word from. */
export function searchGuide(entries: GuideEntry[], query: string): GuideEntry[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return entries;
  return entries.filter((entry) => [entry.title, entry.summary, entry.cost, entry.requires, entry.tip, ...entry.detail]
    .some((field) => field?.toLowerCase().includes(needle)));
}
