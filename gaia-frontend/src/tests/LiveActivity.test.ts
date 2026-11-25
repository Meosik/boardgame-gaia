import { describe, expect, it } from 'vitest';
import { aiHoldNotice, aiStallWarning, liveActionEntries, liveHighlight, opponentLastMoves, turnStatus } from '../liveActivity';
import type { GameEvent, GameState, PlayerState } from '../types/game';

const players = [
  { player_id: 0, nickname: '나' },
  { player_id: 1, nickname: '영희' },
] as PlayerState[];

function state(overrides: Partial<GameState> = {}): GameState {
  return {
    players,
    turn_order: [0, 1],
    phase: { ActionPhase: { active_player: 0 } },
    round: 1,
    ...overrides,
  } as unknown as GameState;
}

/** One server action: its events followed by the `ActionLog` boundary marker the engine writes. */
const buildMine: GameEvent[] = [
  { ResourceChanged: { player: 1, delta: { ore: -1, credits: -2 } } },
  { StructureBuilt: { player: 1, hex: '1,-1', kind: 'Mine' } },
  { ResearchAdvanced: { player: 1, track: 'ArtificialIntelligence', level: 1 } },
  { ActionLog: { player: 1, action: 'Build', event_count: 3 } },
];

describe('liveActionEntries', () => {
  it('describes one action per server action and names the actor', () => {
    const entries = liveActionEntries(buildMine, players);

    expect(entries).toHaveLength(1);
    expect(entries[0].player).toBe(1);
    expect(entries[0].text).toContain('영희');
    expect(entries[0].text).toContain('광산 건설');
    expect(entries[0].details.join(' ')).toContain('광석');
  });

  it('returns nothing for an empty log', () => {
    expect(liveActionEntries(undefined, players)).toEqual([]);
  });
});

describe('liveHighlight', () => {
  it('collects the hexes and research track the last action touched', () => {
    const entry = liveActionEntries(buildMine, players)[0];
    const highlight = liveHighlight(buildMine, entry);

    expect(highlight?.player).toBe(1);
    expect(highlight?.hexes.has('1,-1')).toBe(true);
    // `ResearchBoard` marks tokens by the `ResearchTracks` field name, not the wire track name.
    expect(highlight?.research.has('ai')).toBe(true);
    expect(highlight?.label).toBe(entry.text);
  });

  it('maps an explored ship index to the board name and reads booster ids', () => {
    const events: GameEvent[] = [
      { ShipExplored: { player: 0, ship_id: 2 } },
      { ActionLog: { player: 0, action: 'ExploreSpaceship', event_count: 1 } },
      { PlayerPassed: { player: 0, booster: 7 } },
      { ActionLog: { player: 0, action: 'Pass', event_count: 1 } },
    ];
    const entries = liveActionEntries(events, players);

    expect(liveHighlight(events, entries[0])?.ship).toBe('TFMars');
    expect(liveHighlight(events, entries[1])?.booster).toBe(7);
  });

  it('reads the power-action space from the action marker', () => {
    const events: GameEvent[] = [
      { ResourceChanged: { player: 1, delta: { credits: 7 } } },
      { ActionLog: { player: 1, action: 'PowerAction', event_count: 1, power_action: 4 } },
      // A log saved before the server named the space: nothing to mark.
      { ResourceChanged: { player: 1, delta: { credits: 7 } } },
      { ActionLog: { player: 1, action: 'PowerAction', event_count: 1 } },
    ];
    const entries = liveActionEntries(events, players);

    expect(liveHighlight(events, entries[0])?.powerAction).toBe(4);
    expect(liveHighlight(events, entries[1])?.powerAction).toBeNull();
  });

  it('has nothing to highlight without a recent action', () => {
    expect(liveHighlight(buildMine, null)).toBeNull();
  });
});

describe('opponentLastMoves', () => {
  // The opponent (1) builds a mine, the viewing player (0) builds, the opponent charges off it.
  const events: GameEvent[] = [
    ...buildMine,
    { StructureBuilt: { player: 0, hex: '0,0', kind: 'Mine' } },
    { ActionLog: { player: 0, action: 'Build', event_count: 1 } },
    { ResourceChanged: { player: 1, delta: { credits: -1 } } },
    { ActionLog: { player: 1, action: 'ChargePower', event_count: 1 } },
  ];

  it("keeps an opponent's move when that opponent then only charges power", () => {
    const moves = opponentLastMoves(events, liveActionEntries(events, players), 0);

    expect([...moves.keys()]).toEqual([1]);
    expect(moves.get(1)?.text).toContain('광산 건설');
    expect(moves.get(1)?.hexes.has('1,-1')).toBe(true);
    // What the move touched off the map is kept too: the research step that came with it.
    expect([...(moves.get(1)?.research ?? [])]).toEqual(['ai']);
    expect(moves.get(1)?.booster).toBeNull();
  });

  it('replaces the move when the opponent moves again and leaves out the viewing player', () => {
    const later: GameEvent[] = [
      ...events,
      { PlayerPassed: { player: 1, booster: 7 } },
      { ActionLog: { player: 1, action: 'Pass', event_count: 1 } },
    ];
    const moves = opponentLastMoves(later, liveActionEntries(later, players), 0);

    expect(moves.get(1)?.text).toContain('패스');
    expect(moves.get(1)?.hexes.size).toBe(0);
    expect(moves.get(1)?.research.size).toBe(0);
    expect(moves.get(1)?.booster).toBe(7);
    expect(moves.has(0)).toBe(false);
  });

  it('keeps the action space the move took: a power action and a ship action', () => {
    const power: GameEvent[] = [
      { ResourceChanged: { player: 1, delta: { credits: 7 } } },
      { ActionLog: { player: 1, action: 'PowerAction', event_count: 1, power_action: 4 } },
    ];
    const powerMove = opponentLastMoves(power, liveActionEntries(power, players), 0).get(1);
    expect(powerMove?.powerAction).toBe(4);
    expect(powerMove?.shipAction).toBeNull();

    // The ship space comes from the action's name (`SPACESHIP_ACTION_SPACES`): Rebellion's space 4.
    const ship: GameEvent[] = [
      { ResourceChanged: { player: 1, delta: { credits: 2, qic: 1 } } },
      { ActionLog: { player: 1, action: 'RebellionCreditsAndQic', event_count: 1 } },
    ];
    const shipMove = opponentLastMoves(ship, liveActionEntries(ship, players), 0).get(1);
    expect(shipMove?.shipAction).toBe(4);
    expect(shipMove?.powerAction).toBeNull();
  });

  it.each([
    'ChargePower',
    'TaklonsChargePower',
    'ChooseIncomeOrder',
    'TerransGaiaConversion',
    'ItarsGaiaTechChoice',
    'ItarsGaiaTechTile',
    'FinishGaiaDecision',
    'SelectTinkeringTile',
    'FreeAction',
  ])('does not let a %s response replace the move', (action) => {
    const answered: GameEvent[] = [
      ...buildMine,
      { ResourceChanged: { player: 1, delta: { credits: -1 } } },
      { ActionLog: { player: 1, action, event_count: 1 } },
    ];
    const moves = opponentLastMoves(answered, liveActionEntries(answered, players), 0);

    expect(moves.get(1)?.text).toContain('광산 건설');
    expect(moves.get(1)?.hexes.has('1,-1')).toBe(true);
  });
});

describe('aiStallWarning', () => {
  it('speaks only while the server reports that the AI seats stopped', () => {
    expect(aiStallWarning(null)).toBeNull();
    expect(aiStallWarning(state())).toBeNull();
    expect(aiStallWarning(state({ ai_stalled: null }))).toBeNull();
    expect(aiStallWarning(state({ ai_stalled: { revision: 7, player: 1, reason: 'no_answer' } }))).toBe(
      '⚠ AI 교사 응답 없음 — 영희 차례에서 멈춤 (교사가 답하지 못함)',
    );
    expect(aiStallWarning(state({ ai_stalled: { revision: 7, player: 9, reason: 'rejected' } }))).toBe(
      '⚠ AI 교사 응답 없음 — 플레이어 9 차례에서 멈춤 (교사가 낸 수를 엔진이 거부함)',
    );
    // The server's own failure, not the teacher's: a different line, the same retry button.
    expect(aiStallWarning(state({ ai_stalled: { revision: 7, player: 1, reason: 'server_error' } }))).toBe(
      '⚠ AI 진행 멈춤 — 영희의 수 뒤에 서버가 다음 단계로 넘어가지 못함',
    );
  });
});

describe('aiHoldNotice', () => {
  it('speaks only while the AI seats wait at a finished AI turn', () => {
    expect(aiHoldNotice(null)).toBeNull();
    expect(aiHoldNotice(state({ ai_review: true }))).toBeNull();
    const turn = { player: 1, start_revision: 5, revision: 7, decisions: [] };
    const hold = { revision: 7, turn, rejections: 0, spares_left: null, can_reject: true };
    expect(aiHoldNotice(state({ ai_review: true, ai_hold: hold }))).toBe(
      '⏸ AI 멈춤 — 영희의 차례가 끝났습니다. 「AI 차례 검토」에서 계속하거나 거절하세요.',
    );
    // No move of the teacher is left for a rejected turn: the player plays it.
    expect(aiHoldNotice(state({ ai_review: true, ai_takeover: { player: 1, rejections: 3 } }))).toBe(
      '✋ 영희의 차례를 직접 두세요 — 교사가 낼 다른 수가 없습니다. 차례가 끝날 때까지 이 좌석으로 둡니다.',
    );
  });
});

describe('turnStatus', () => {
  it('tells the acting player what to do', () => {
    const status = turnStatus(state(), 0);

    expect(status).toMatchObject({ mine: true });
    expect(status?.text).toBe('내 차례입니다');
    expect(status?.hint).toContain('자유 행동');
  });

  it('names the player everyone else is waiting for', () => {
    const status = turnStatus(state({ phase: { ActionPhase: { active_player: 1 } } }), 0);

    expect(status).toMatchObject({ mine: false });
    expect(status?.text).toBe('영희님 차례 — 기다리는 중');
  });

  it('explains a pending power-charge decision on both sides', () => {
    const phase = {
      ChargePowerPending: {
        queue: [{ player: 1, hex: { q: 0, r: 0 }, max_power: 2 }],
        resume_active_player: 0,
      },
    } as unknown as GameState['phase'];

    expect(turnStatus(state({ phase }), 1)).toMatchObject({
      mine: true,
      text: '내 차례: 파워 충전 여부 선택',
    });
    expect(turnStatus(state({ phase }), 0)).toMatchObject({
      mine: false,
      text: '영희님이 파워 충전 여부 선택 중 — 기다리는 중',
    });
  });

  it('reports setup and between-round phases instead of a turn', () => {
    const setup = { Setup: { FactionSelection: { active_player: 1 } } } as unknown as GameState['phase'];
    expect(turnStatus(state({ phase: setup }), 0)?.text).toBe('영희님 종족 선택 중 — 기다리는 중');
    expect(turnStatus(state({ phase: 'IncomePhase' }), 0)?.text).toBe('수입 단계 진행 중');
    expect(turnStatus(state({ phase: 'GaiaPhase' }), 0)?.mine).toBe(false);
  });
});
