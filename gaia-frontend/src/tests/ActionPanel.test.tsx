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
    setup_bid_vp: 0,
    passed: false,
    federation_tokens: [],
    alliance_tiles: [],
    explored_ships: [],
    exploration_shuttles_available: 3,
    gaiaformers_total: 3,
    gaiaformers_deployed: 0,
    gaiaformers_in_gaia_area: 0,
    academy_qic_action_used_this_round: false,
    gleens_special_action_used_this_round: false,
    space_giants_special_action_used_this_round: false,
    ...overrides,
  };
}

function mockGameState(overrides: Partial<GameState> = {}): GameState {
  return {
    players: [mockPlayer({ player_id: 0 }), mockPlayer({ player_id: 1, nickname: 'P1' })],
    board: { sectors: [], hexes: {}, lost_planet: null, spaceship_tiles: {} },
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
    bidding: null,
    turn_order: [0, 1],
    current_player: 0,
    used_power_actions: [],
    spaceship_boards: [],
    used_spaceship_actions: [],
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

  it('hides unsupported faction special actions', () => {
    render(<ActionPanel gameState={mockGameState()} myPlayerId={0} />);

    expect(screen.queryByText('특수 능력')).not.toBeInTheDocument();
  });

  it('shows an implemented faction special action', () => {
    const state = mockGameState({ players: [mockPlayer({ faction: 'SpaceGiants' })] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText('특수 능력')).toBeInTheDocument();
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

describe('ActionPanel — base faction actions', () => {
  it('sends the Ambas PI-to-Mine swap with the selected Mine coordinate', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'Ambas',
          structures: [
            { hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' },
            { hex: { q: 1, r: 0 }, kind: 'Mine' },
          ],
        }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Ambas 행성의회 ↔ 광산 교환'));
    act(() => useGameStore.setState({ activePlanet: { q: 1, r: 0 } }));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'AmbasSwapPlanetaryInstitute',
      mine_coord: { q: 1, r: 0 },
    });
    expect(screen.queryByText('Firaks 연구소 강등 + 무료 연구')).not.toBeInTheDocument();
  });

  it('sends the Firaks downgrade target and chosen free research track', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'Firaks',
          structures: [
            { hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' },
            { hex: { q: 1, r: 0 }, kind: 'ResearchLab' },
          ],
        }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Firaks 연구소 강등 + 무료 연구'));
    fireEvent.click(screen.getByText('과학'));
    act(() => useGameStore.setState({ activePlanet: { q: 1, r: 0 } }));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'FiraksDowngradeResearchLab',
      coord: { q: 1, r: 0 },
      track: 'Science',
    });
  });

  it('allows Bescods to select only a currently lowest research track', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'Bescods',
          research_tracks: {
            terraforming: 2,
            navigation: 1,
            ai: 1,
            gaia: 1,
            economy: 1,
            science: 1,
          },
        }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Bescods 최저 연구 무료 상승'));
    expect(screen.getByText('테라포밍')).toBeDisabled();
    fireEvent.click(screen.getByText('항법'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'BescodsLowestResearchAdvance',
      track: 'Navigation',
    });
  });

  it('disables a base faction action after its round token was used', () => {
    const state = mockGameState({
      players: [
        mockPlayer({ faction: 'Bescods', faction_special_action_used_this_round: true }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(
      screen.getByText(/Bescods 최저 연구 무료 상승.*사용됨/).closest('button'),
    ).toBeDisabled();
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

  it('requires an available replacement when the player owns a booster', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [mockPlayer({ booster: 7 })],
      boosters: [8, 9, 10],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByAltText('라운드 부스터 7')).toBeInTheDocument();
    expect(screen.getByText('새 부스터를 선택하세요')).toBeDisabled();
    fireEvent.click(screen.getByAltText('라운드 부스터 8'));
    fireEvent.click(screen.getByText('패스'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'Pass', booster_id: 8 });
  });
});

describe('ActionPanel — free actions', () => {
  it('sends a FreeAction without needing selectedAction/confirm', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('광석 1 → 크레딧 1'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'FreeAction', kind: 'OreToCredit', count: 1 });
  });

  it('shows only the current faction free-action extensions', () => {
    const xenos = mockPlayer({ faction: 'Xenos' });
    const state = mockGameState({ players: [xenos] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText('광석 1 → 파워 1(3단계) (Xenos)')).toBeInTheDocument();
    expect(screen.queryByText(/Hadsch Hallas/)).not.toBeInTheDocument();
  });

  it('reveals Hadsch Hallas credit conversions only after building the PI', () => {
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'HadschHallas',
          structures: [{ hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' }],
        }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText('크레딧 3 → 광석 1 (Hadsch Hallas)')).toBeInTheDocument();
  });

  it('disables conversions the player cannot afford', () => {
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText('파워 4 → QIC 1')).toBeDisabled();
    expect(screen.getByText('광석 1 → 크레딧 1')).not.toBeDisabled();
  });

  it('sends multiple conversions as one atomic action', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.change(screen.getByLabelText('광석 1 → 크레딧 1 수량'), { target: { value: '3' } });
    fireEvent.click(screen.getByText('광석 1 → 크레딧 1'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'FreeAction', kind: 'OreToCredit', count: 3 });
  });
});

describe('ActionPanel — shared power action slots', () => {
  it('disables a power action slot already taken this round', () => {
    const state = mockGameState({ used_power_actions: [1] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('파워 액션'));

    expect(screen.getByText(/파워 7 → 지식 3.*사용됨/)).toBeDisabled();
    expect(screen.getByText('파워 4 → 광석 2')).not.toBeDisabled();
  });

  it('sends a no-coord power action immediately when clicked', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('파워 액션'));
    fireEvent.click(screen.getByText('파워 4 → 광석 2'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'PowerAction', id: 3, coord: null });
  });

  it('requires a target hex before confirming a terraforming-step power action', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('파워 액션'));
    fireEvent.click(screen.getByText('파워 5 → 광산 건설 (테라포밍 2단계 무료)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();
    expect(sendAction).not.toHaveBeenCalled();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 1, r: -1 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'PowerAction',
      id: 2,
      coord: { q: 1, r: -1 },
    });
  });
});

describe('ActionPanel — Gaia round-booster special actions', () => {
  it('shows booster 5 immediate Gaia formation and sends its target', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({ players: [mockPlayer({ booster: 5 })] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('부스터 즉시 가이아포밍'));
    act(() => {
      useGameStore.setState({ activePlanet: { q: 2, r: -1 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'RoundBoosterImmediateGaiaFormation',
      coord: { q: 2, r: -1 },
    });
  });

  it('shares booster 8 usage across Build, Gaia, and spaceship exploration modes', () => {
    const state = mockGameState({
      players: [
        mockPlayer({
          booster: 8,
          round_booster_special_action_used_this_round: true,
        }),
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText(/부스터 \+3 사거리 광산 건설.*사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/부스터 \+3 사거리 가이아 프로젝트.*사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/부스터 \+3 사거리 함선 탐사.*사용됨/).closest('button')).toBeDisabled();
  });

  it('sends booster 8 +3-range spaceship exploration with the selected ship', () => {
    const sendAction = vi.fn();
    useGameStore.setState((state) => ({ actions: { ...state.actions, sendAction } }));
    const state = mockGameState({ players: [mockPlayer({ booster: 8 })] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('부스터 +3 사거리 함선 탐사'));
    fireEvent.click(screen.getByText('Eclipse'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'RoundBoosterRangeExploreSpaceship',
      ship: 'Eclipse',
    });
  });

  it('does not show a round-booster special action without owning that booster', () => {
    render(<ActionPanel gameState={mockGameState()} myPlayerId={0} />);

    expect(screen.queryByText('부스터 즉시 가이아포밍')).not.toBeInTheDocument();
    expect(screen.queryByText('부스터 +3 사거리 가이아 프로젝트')).not.toBeInTheDocument();
    expect(screen.queryByText('부스터 +3 사거리 함선 탐사')).not.toBeInTheDocument();
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

  it('lets Taklons with their PI choose when the bonus power token is gained', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'Taklons',
          structures: [{ hex: { q: 0, r: 0 }, kind: 'PlanetaryInstitute' }],
        }),
        mockPlayer({ player_id: 1, nickname: 'P1' }),
      ],
      phase: {
        ChargePowerPending: {
          queue: [{ player: 0, hex: { q: 0, r: 0 }, max_power: 3 }],
          resume_active_player: 1,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('파워 토큰을 먼저 받고 충전'));
    expect(sendAction).toHaveBeenCalledWith({
      type: 'TaklonsChargePower',
      gain_before: true,
    });
    fireEvent.click(screen.getByText('충전 후 파워 토큰 받기'));
    expect(sendAction).toHaveBeenCalledWith({
      type: 'TaklonsChargePower',
      gain_before: false,
    });
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

describe('ActionPanel — GaiaDecisionPending', () => {
  it('lets Terrans convert Gaia-area power and finish the phase', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'Terrans',
          resources: {
            ...mockPlayer().resources,
            power: { ...mockPlayer().resources.power, gaia_forming: 4 },
          },
        }),
      ],
      phase: {
        GaiaDecisionPending: {
          queue: [{ player: 0, kind: 'TerransPowerConversion', remaining_power: 4 }],
          round: 1,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('가이아 파워 3 → 광석 1'));
    fireEvent.click(screen.getByText('가이아 단계 완료'));

    expect(sendAction).toHaveBeenNthCalledWith(1, {
      type: 'TerransGaiaConversion',
      kind: 'PowerToOre',
      count: 1,
    });
    expect(sendAction).toHaveBeenNthCalledWith(2, { type: 'FinishGaiaDecision' });
  });

  it('lets Itars choose a Standard Tech tile and research track', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [
        mockPlayer({
          faction: 'Itars',
          resources: {
            ...mockPlayer().resources,
            power: { ...mockPlayer().resources.power, gaia_forming: 8 },
          },
        }),
      ],
      research_board: {
        ...mockGameState().research_board,
        tech_tiles: [1, 2],
      },
      phase: {
        GaiaDecisionPending: {
          queue: [{ player: 0, kind: 'ItarsTechTile', remaining_power: 8 }],
          round: 1,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('기술 타일 #2'));
    fireEvent.click(screen.getByText('과학'));
    fireEvent.click(screen.getByText('파워 4로 기술 타일 획득'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'ItarsGaiaTechTile',
      tile: 2,
      track: 'Science',
    });
  });

  it('shows a waiting message to players outside the Gaia decision queue', () => {
    const state = mockGameState({
      phase: {
        GaiaDecisionPending: {
          queue: [{ player: 1, kind: 'TerransPowerConversion', remaining_power: 4 }],
          round: 1,
        },
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText(/P1.*가이아 단계 능력/)).toBeInTheDocument();
  });
});

describe('ActionPanel — Lost Fleet: Explore a Spaceship / Examine an Artifact', () => {
  it('disables spaceship action spaces already covered this round', () => {
    const state = mockGameState({ used_spaceship_actions: [1, 5] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText(/함선 크레딧 액션.*이번 라운드 사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/T F Mars QIC 액션.*이번 라운드 사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText('Twilight 무료 업그레이드 (교역소→연구소)').closest('button')).toBeEnabled();
  });

  it('requires selecting a spaceship before confirming Explore', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('함선 탐사'));
    expect(screen.queryByText('확인')).not.toBeInTheDocument();

    fireEvent.click(screen.getByText('Twilight'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'ExploreSpaceship', ship: 'Twilight' });
  });

  it('disables a spaceship the player has already explored', () => {
    const state = mockGameState({
      spaceship_boards: [
        {
          id: 'Twilight',
          explorers: [0, null, null, null],
          artifact_pool: [1],
          federation_token: null,
        },
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('함선 탐사'));
    expect(screen.getByText(/Twilight.*탐사 완료/)).toBeDisabled();
  });

  it('sends ExamineArtifact once an artifact is chosen and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      spaceship_boards: [
        {
          id: 'Twilight',
          explorers: [0, null, null, null],
          artifact_pool: [8],
          federation_token: null,
        },
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('아티팩트 조사'));
    fireEvent.click(screen.getByText('7점'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'ExamineArtifact',
      artifact: 8,
      copy_federation_token_kind: null,
      bonus_build_coord: null,
      bonus_tech_tile: null,
      bonus_research_track: null,
    });
  });

  it('sends SpaceshipCreditTerraform once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('함선 크레딧 액션 (테라포밍 1단계 무료)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 1, r: -1 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'SpaceshipCreditTerraform',
      coord: { q: 1, r: -1 },
    });
  });

  it('sends TwilightFreeResearchLab once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Twilight 무료 업그레이드 (교역소→연구소)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 2, r: -2 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'TwilightFreeResearchLab',
      coord: { q: 2, r: -2 },
    });
  });

  it('sends RebellionFreeTradingStation once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Rebellion 무료 업그레이드 (광산→교역소)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 3, r: -3 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'RebellionFreeTradingStation',
      coord: { q: 3, r: -3 },
    });
  });

  it('sends RebellionCreditsAndQic immediately on confirm', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Rebellion 지식 액션 (지식 2 → 크레딧 2 + QIC 1)'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'RebellionCreditsAndQic' });
  });

  it('disables all Twilight +3-range target modes when their shared slot is used', () => {
    const state = mockGameState({ used_spaceship_actions: [11] });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    expect(screen.getByText(/Twilight \+3 사거리 광산 건설.*사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Twilight \+3 사거리 가이아 프로젝트.*사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Twilight \+3 사거리 함선 탐사.*사용됨/).closest('button')).toBeDisabled();
  });

  it('sends Twilight federation-token replay for an owned token', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      players: [mockPlayer({ federation_tokens: [5] })],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Twilight 연방 토큰 효과 재사용 (QIC 3)'));
    fireEvent.click(screen.getByText('7점 + 크레딧 6'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'TwilightReplayFederationToken',
      token_kind: 5,
      bonus_build_coord: null,
      bonus_tech_tile: null,
      bonus_research_track: null,
    });
  });

  it('sends Twilight +3-range Gaia formation once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((state) => ({ actions: { ...state.actions, sendAction } }));
    render(<ActionPanel gameState={mockGameState()} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Twilight +3 사거리 가이아 프로젝트 (지식 1)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 6, r: -6 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'TwilightRangeGaiaFormation',
      coord: { q: 6, r: -6 },
    });
  });

  it('sends Twilight +3-range spaceship exploration with the selected ship', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    render(<ActionPanel gameState={mockGameState()} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Twilight +3 사거리 함선 탐사 (지식 1)'));
    fireEvent.click(screen.getByText('Rebellion'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'TwilightRangeExploreSpaceship',
      ship: 'Rebellion',
    });
  });

  it('sends Gleens and Space Giants public special-action payloads and gates them by faction/use token', () => {
    const sendAction = vi.fn();
    useGameStore.setState((state) => ({ actions: { ...state.actions, sendAction } }));
    const gleensState = mockGameState({ players: [mockPlayer({ faction: 'Gleens' })] });
    const { rerender } = render(<ActionPanel gameState={gleensState} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Gleens 특수 능력: 광산 건설 (+2 사거리)'));
    act(() => {
      useGameStore.setState({ activePlanet: { q: 7, r: -7 } });
    });
    fireEvent.click(screen.getByText('확인'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'GleensBuildMine', coord: { q: 7, r: -7 } });

    fireEvent.click(screen.getByText('Gleens 특수 능력: 가이아 프로젝트 (+2 사거리)'));
    act(() => {
      useGameStore.setState({ activePlanet: { q: 8, r: -8 } });
    });
    fireEvent.click(screen.getByText('확인'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'GleensGaiaFormation', coord: { q: 8, r: -8 } });

    fireEvent.click(screen.getByText('Gleens 특수 능력: 함선 탐사 (+2 사거리)'));
    fireEvent.click(screen.getByText('T F Mars'));
    fireEvent.click(screen.getByText('확인'));
    expect(sendAction).toHaveBeenCalledWith({ type: 'GleensExploreSpaceship', ship: 'TFMars' });

    rerender(
      <ActionPanel
        gameState={mockGameState({
          players: [
            mockPlayer({ faction: 'Gleens', gleens_special_action_used_this_round: true }),
          ],
        })}
        myPlayerId={0}
      />,
    );
    expect(screen.getByText(/Gleens 특수 능력: 광산 건설.*사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Gleens 특수 능력: 가이아 프로젝트.*사용됨/).closest('button')).toBeDisabled();
    expect(screen.getByText(/Gleens 특수 능력: 함선 탐사.*사용됨/).closest('button')).toBeDisabled();

    rerender(<ActionPanel gameState={mockGameState()} myPlayerId={0} />);
    expect(screen.queryByText('Gleens 특수 능력: 광산 건설 (+2 사거리)')).not.toBeInTheDocument();
    expect(screen.queryByText('Gleens 특수 능력: 가이아 프로젝트 (+2 사거리)')).not.toBeInTheDocument();
    expect(screen.queryByText('Gleens 특수 능력: 함선 탐사 (+2 사거리)')).not.toBeInTheDocument();

    rerender(
      <ActionPanel
        gameState={mockGameState({ players: [mockPlayer({ faction: 'SpaceGiants' })] })}
        myPlayerId={0}
      />,
    );
    fireEvent.click(screen.getByText('Space Giants 특수 능력: 광산 건설 (테라포밍 2단계 무료)'));
    act(() => {
      useGameStore.setState({ activePlanet: { q: 9, r: -9 } });
    });
    fireEvent.click(screen.getByText('확인'));
    expect(sendAction).toHaveBeenCalledWith({
      type: 'SpaceGiantsBuildMine',
      coord: { q: 9, r: -9 },
    });

    rerender(
      <ActionPanel
        gameState={mockGameState({
          players: [
            mockPlayer({ faction: 'SpaceGiants', space_giants_special_action_used_this_round: true }),
          ],
        })}
        myPlayerId={0}
      />,
    );
    expect(screen.getByText(/Space Giants 특수 능력: 광산 건설.*사용됨/).closest('button')).toBeDisabled();

    rerender(<ActionPanel gameState={mockGameState()} myPlayerId={0} />);
    expect(
      screen.queryByText('Space Giants 특수 능력: 광산 건설 (테라포밍 2단계 무료)'),
    ).not.toBeInTheDocument();
  });

  it('sends Rebellion tech-tile action after choosing a tile and research track', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const base = mockGameState();
    const state = mockGameState({
      research_board: { ...base.research_board, tech_tiles: [2, 4] },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Rebellion 표준 기술 타일 획득 (QIC 3)'));
    fireEvent.click(screen.getByText('기술 타일 #2'));
    fireEvent.click(screen.getByText('과학'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'RebellionGainTechTile',
      tile: 2,
      track: 'Science',
    });
  });

  it('sends TFMarsTechBonus immediately on confirm', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('T F Mars QIC 액션 (QIC 2 → 2 + 기술 타일당 1점)'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'TFMarsTechBonus' });
  });

  it('sends TFMarsGaiaFormation once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('T F Mars 즉시 가이아포밍 (파워 2)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 4, r: -4 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'TFMarsGaiaFormation',
      coord: { q: 4, r: -4 },
    });
  });

  it('sends EclipsePlanetTypeBonus immediately on confirm', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Eclipse QIC 액션 (QIC 2 → 2 + 행성 종류당 1점)'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({ type: 'EclipsePlanetTypeBonus' });
  });

  it('sends EclipseResearchBoost once a track is picked', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Eclipse 연구 부스트 (파워 3 + 지식 2)'));
    fireEvent.click(screen.getByText('과학'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'EclipseResearchBoost',
      track: 'Science',
    });
  });

  it('sends EclipseAsteroidMine once a hex is selected and confirmed', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState();
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('Eclipse 소행성 광산 (크레딧 6)'));
    expect(screen.getByText('보드에서 대상 헥스를 선택하세요')).toBeInTheDocument();

    act(() => {
      useGameStore.setState({ activePlanet: { q: 5, r: -5 } });
    });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'EclipseAsteroidMine',
      coord: { q: 5, r: -5 },
    });
  });
});

describe('ActionPanel — FormFederation token choice', () => {
  it('sends a Supply token choice once hexes and a token kind are picked', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      research_board: {
        ...mockGameState().research_board,
        federation_tokens: [1, 2, 2],
      },
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('연방 형성'));
    act(() => {
      useGameStore.setState({ selectedHexes: [{ q: 0, r: 0 }, { q: 1, r: 0 }] });
    });
    fireEvent.click(screen.getByText('8점 + QIC 1'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'FormFederation',
      hexes: [{ q: 0, r: 0 }, { q: 1, r: 0 }],
      satellite_hexes: [],
      token: { source: 'Supply', kind: 2 },
      bonus_build_coord: null,
      bonus_tech_tile: null,
    });
  });

  it('sends a Spaceship token choice for an explored ship with an unclaimed token', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      spaceship_boards: [
        {
          id: 'Twilight',
          explorers: [0, null, null, null],
          artifact_pool: [],
          federation_token: 9,
        },
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('연방 형성'));
    act(() => {
      useGameStore.setState({ selectedHexes: [{ q: 0, r: 0 }] });
    });
    fireEvent.click(screen.getByText('Twilight: [함선] 12점'));
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'FormFederation',
      hexes: [{ q: 0, r: 0 }],
      satellite_hexes: [],
      token: { source: 'Spaceship', ship: 'Twilight' },
      bonus_build_coord: null,
      bonus_tech_tile: null,
    });
  });

  it('requires a bonus build coord before confirming a free-build token kind', () => {
    const sendAction = vi.fn();
    useGameStore.setState((s) => ({ actions: { ...s.actions, sendAction } }));
    const state = mockGameState({
      spaceship_boards: [
        {
          id: 'Twilight',
          explorers: [0, null, null, null],
          artifact_pool: [],
          federation_token: 15, // unlimited-range free build
        },
      ],
    });
    render(<ActionPanel gameState={state} myPlayerId={0} />);

    fireEvent.click(screen.getByText('연방 형성'));
    act(() => {
      useGameStore.setState({ selectedHexes: [{ q: 0, r: 0 }] });
    });
    fireEvent.click(screen.getByText(/\[함선\] 무제한 사거리/));
    expect(screen.queryByText('확인')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('보너스 광산 좌표 q'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText('보너스 광산 좌표 r'), { target: { value: '-2' } });
    fireEvent.click(screen.getByText('확인'));

    expect(sendAction).toHaveBeenCalledWith({
      type: 'FormFederation',
      hexes: [{ q: 0, r: 0 }],
      satellite_hexes: [],
      token: { source: 'Spaceship', ship: 'Twilight' },
      bonus_build_coord: { q: 3, r: -2 },
      bonus_tech_tile: null,
    });
  });
});
