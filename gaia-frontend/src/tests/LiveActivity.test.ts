import { describe, expect, it } from 'vitest';
import { liveActionEntries, liveHighlight, turnStatus } from '../liveActivity';
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

  it('has nothing to highlight without a recent action', () => {
    expect(liveHighlight(buildMine, null)).toBeNull();
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
