import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { ActionPanel } from '../components/ActionPanel';
import { useGameStore } from '../store/gameStore';
import type { GameState, PlayerState } from '../types/game';

function mockPlayer(overrides: Partial<PlayerState> = {}): PlayerState {
  return {
    player_id: 0,
    nickname: 'P0',
    faction: 'Terrans',
    resources: {
      ore: 4,
      credits: 15,
      knowledge: 3,
      qic: 1,
      power: { bowl1: 4, bowl2: 4, bowl3: 0, gaia_bowl: 0, gaia_forming: 0 },
      spent_gaia_formers: 0,
    },
    structures: [],
    research_tracks: { terraforming: 0, navigation: 0, ai: 0, gaia: 0, economy: 0, science: 0 },
    vp: 10,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    academy_qic_action_used_this_round: false,
    ...overrides,
  };
}

function mockGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    players: [mockPlayer({ player_id: 0 }), mockPlayer({ player_id: 1, nickname: 'P1' })],
    board: { sectors: [], hexes: {}, lost_planet: null },
    research_board: {
      tracks: {
        Terraforming: { player_levels: {}, alliance_taken: [] },
        Navigation: { player_levels: {}, alliance_taken: [] },
        ArtificialIntelligence: { player_levels: {}, alliance_taken: [] },
        GaiaProject: { player_levels: {}, alliance_taken: [] },
        Economy: { player_levels: {}, alliance_taken: [] },
        Science: { player_levels: {}, alliance_taken: [] },
      },
      tech_tiles: [],
      advanced_tech_tiles: [null, null, null, null, null, null],
      federation_tokens: [],
    },
    round: 1,
    phase: { ActionPhase: { active_player: 0 } },
    round_tiles: [],
    final_scoring_tiles: [],
    boosters: [],
    faction_selection: null,
    turn_order: [0, 1],
    current_player: 0,
    used_power_actions: [],
    used_qic_action_slots: [],
    ...overrides,
  };
}

beforeEach(() => {
  useGameStore.setState({
    gameState: null,
    myPlayerId: null,
    activePlanet: null,
    selectedHexes: [],
    selectedAction: null,
    wsClient: null,
  });
});

describe('ActionPanel — turn gating', () => {
  it('shows a waiting message when it is not my turn', () => {
    const state = mockGameState({ phase: { ActionPhase: { active_player: 1 } } });
    render(<ActionPanel gameState={state} myPlayerId={0} />);
    expect(screen.getByText(/P1.*턴입니다/)).toBeInTheDocument();
  });

  it('shows the action menu when it is my turn', () => {
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);
    expect(screen.getByText('광산 건설')).toBeInTheDocument();
    expect(screen.getByText('패스')).toBeInTheDocument();
  });
});

describe('ActionPanel — Build flow', () => {
  it('sends a Build action once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('광산 건설'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 1, r: -1 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'Build', coord: { q: 1, r: -1 } });
  });
});

describe('ActionPanel — Pass', () => {
  it('sends a Pass action with a null booster_id when none is selected', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('패스'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'Pass', booster_id: null });
  });
});

describe('ActionPanel — shared power/QIC action slots', () => {
  it('disables a power action slot already taken this round', () => {
    const state = mockGameState({ used_power_actions: [1] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('파워 액션'));

    expect(screen.getByText(/파워 3 → 광석 3.*사용됨/)).toBeDisabled();
    expect(screen.getByText('파워 4 → 광석 2')).not.toBeDisabled();
  });

  it('disables a QIC action slot already taken this round', () => {
    const state = mockGameState({ used_qic_action_slots: [1] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('QIC 액션'));

    expect(screen.getByText(/QIC 1 → 광석 1.*사용됨/)).toBeDisabled();
    expect(screen.getByText('QIC 1 → 연구 1단계')).not.toBeDisabled();
  });
});

describe('ActionPanel — Academy(Qic) action', () => {
  it('is hidden without an Academy(Qic) structure', () => {
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);
    expect(screen.queryByText(/아카데미\(QIC\) 행동/)).not.toBeInTheDocument();
  });

  it('sends AcademyQicAction when the player owns an Academy(Qic)', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          player_id: 0,
          structures: [{ hex: { q: 0, r: 0 }, kind: { Academy: 'Qic' } }],
        }),
        mockPlayer({ player_id: 1, nickname: 'P1' }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText(/아카데미\(QIC\) 행동/));

    expect(sendAction).toHaveBeenCalledWith({ type: 'AcademyQicAction' });
  });

  it('is disabled once already used this round', () => {
    const state = mockGameState({
      players: [
        mockPlayer({
          player_id: 0,
          structures: [{ hex: { q: 0, r: 0 }, kind: { Academy: 'Qic' } }],
          academy_qic_action_used_this_round: true,
        }),
        mockPlayer({ player_id: 1, nickname: 'P1' }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText(/이번 라운드 사용 완료/)).toBeDisabled();
  });
});

describe('ActionPanel — ChargePowerPending', () => {
  it('shows accept/decline for the queued player', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      phase: {
        ChargePowerPending: {
          queue: [{ player: 0, hex: { q: 0, r: 0 }, max_power: 3 }],
          resume_active_player: 1,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('충전 (3)'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'ChargePower', accept: true });
  });

  it('shows a waiting message for a non-queued player', () => {
    const state = mockGameState({
      phase: {
        ChargePowerPending: {
          queue: [{ player: 1, hex: { q: 0, r: 0 }, max_power: 3 }],
          resume_active_player: 0,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);
    expect(screen.getByText(/P1.*파워 충전 여부/)).toBeInTheDocument();
  });
});

describe('ActionPanel — IncomeOrderPending', () => {
  it('sends ChooseIncomeOrder with the chosen order', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      phase: {
        IncomeOrderPending: {
          queue: [{ player: 0, charge_amount: 4, bonus_tokens: 1 }],
          round: 1,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('토큰 먼저'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'ChooseIncomeOrder', charge_first: false });
  });
});
