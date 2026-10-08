import { RoundOneGuide } from './components/Tutorial/RoundOneGuide';
import { Tutorial } from './components/Tutorial';
import { currentTutorialStep, tutorialNotice, tutorialTargets, tutorialPanel } from './tutorial/round1';
import type { CoachBoardControls } from './components/AiCoach/boardSelection';
import { GameCommandControls, GameCommandStatus } from './components/GameCommandControls';
import { RewardMotion } from './components/RewardMotion';
import { resourceMotionBatch, type RewardBatch } from './components/RewardMotion/rewards';
import { DevTestControls } from './components/DevTestControls';
import { ActionCancelButton } from './components/ActionCancelButton';
import { shipActionPrerequisiteNotice } from './components/shipActionPreflight';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import { shallow } from 'zustand/shallow';
import { CalibrationView } from './components/CalibrationView';
import { ShuttlePreview } from './components/ShuttlePreview';
import { GameLobby } from './components/GameLobby';
import { TerraformingSelectionBoard } from './components/GameLobby/TerraformingSelectionBoard';
import { GameBoard } from './components/GameBoard';
import { ActionPanel } from './components/ActionPanel';
import { PlayerDashboard } from './components/PlayerDashboard';
import { OpponentPanels } from './components/OpponentPanels';
import { ResearchBoard } from './components/PlayerDashboard/ResearchBoard';
import { RESEARCH_TRACK_ORDER } from './components/PlayerDashboard/ResearchBoard';
import {
  canPayForUpgrade,
  StructureActionPopup,
  type StructurePopupMode,
} from './components/StructureActionPopup';
import { ScoringBoard } from './components/ScoringBoard';
import { PersonalBoardDrawer } from './components/PersonalBoardDrawer';
import { RoundBoosters } from './components/RoundBoosters';
import { FederationTokens } from './components/FederationTokens';
import { SpaceshipBoards } from './components/SpaceshipBoards';
import { SpaceshipExplorePopup } from './components/SpaceshipExplorePopup';
import { LostFleetTechRequirementBoard } from './components/LostFleetTechRequirementBoard';
import {
  informationCubesNeededForRange,
  PlanetActionPopup,
  rangeRequirementNotice,
  type BuildActionPreview,
} from './components/PlanetActionPopup';
import { selectableFederationHexes, validateFederationSelection } from './components/federationSelection';
import { GameLog } from './components/GameLog';
import { SidebarTurnControls } from './components/SidebarTurnControls';
import { TopPassControl } from './components/TopPassControl';
import { PlayerActionShelf } from './components/PlayerActionShelf';
import { GameOverScreen } from './components/GameOverScreen';
import { TurnBanner } from './components/TurnBanner';
import { ActionToast } from './components/ActionToast';
import { RecentActions } from './components/RecentActions';
import { liveActionEntries, liveHighlight, turnStatus } from './liveActivity';
import { ReplayHighlightContext } from './replay/highlight';
import { recentActionHex, scrollBoardIntoView } from './boardScroll';
import { TutorialPanel } from './components/Tutorial/TutorialPanel';
import { FloatingBoardPanel } from './components/FloatingBoardPanel';
import { FACTION_STRUCTURE_COLOR, STRUCTURE_COLOR_HEX } from './assets/structureImages';
import { useGameStore, type FinalResult } from './store/gameStore';
import { useRoomStore } from './store/roomStore';
import { GaiaWebSocket } from './api/websocket';
import type { FederationTokenChoice, GameAction, Hex, HexCoord, ResearchTrack, ServerMessage, SpaceshipId, StructureType, TechTileChoice } from './types/game';
import { activeActionPlayerId, isGameState, pendingDecisionPlayerId } from './types/game';
import { factionDisplayName } from './displayNames';

type AppView = 'lobby' | 'game';

interface BoardStructurePopupState {
  coord: HexCoord;
  structure: StructureType;
  anchor: { x: number; y: number };
}

interface BoardPlanetPopupState {
  hex: Hex;
  anchor: { x: number; y: number };
  powerActionId?: 2 | 6;
  buildAction?: BuildActionPreview;
}

interface BoardSpaceshipPopupState {
  ship: SpaceshipId;
  anchor: { x: number; y: number };
}

type TechFlowCompletion =
  | { kind: 'Upgrade' }
  | { kind: 'TwilightFreeResearchLab' }
  | { kind: 'RebellionGainTechTile' }
  | { kind: 'TwilightReplayFederationToken'; tokenKind: number }
  | { kind: 'FederationBonus' };

type TechUpgradeFlow = {
  coord: HexCoord;
  to: StructureType;
  anchor: { x: number; y: number };
  completion: TechFlowCompletion;
} & (
  | {
      stage: 'tile';
    }
  | {
      stage: 'track';
      tile: number;
    }
  | {
      stage: 'bonus-mine';
      tile: number;
      advanceTrack: ResearchTrack | null;
    }
  | {
      stage: 'cover';
      lostFleet?: boolean;
      tile: number;
      track: ResearchTrack;
    }
  | {
      stage: 'advanced-track';
      lostFleet?: boolean;
      track: ResearchTrack;
      coveredTile: number;
    }
);

const IMMEDIATE_SPACESHIP_ACTIONS = new Set<GameAction['type']>([
  'RebellionCreditsAndQic',
  'TFMarsTechBonus',
  'EclipsePlanetTypeBonus',
]);

const MAP_TARGET_SPACESHIP_ACTIONS = new Set<GameAction['type']>([
  'GleensBuildMine',
  'SpaceGiantsBuildMine',
  'RoundBoosterImmediateGaiaFormation',
  'RoundBoosterRangeBuild',
  'RoundBoosterTerraformBuild',
  'TinkeroidsUseTile',
  'SpaceshipCreditTerraform',
  'TwilightFreeResearchLab',
  'TwilightRangeBuild',
  'TwilightRangeGaiaFormation',
  'TwilightRangeExploreSpaceship',
  'RebellionFreeTradingStation',
  'TFMarsGaiaFormation',
  'EclipseAsteroidMine',
]);

function DraggableActionPopup({
  className,
  label,
  children,
}: {
  className: string;
  label: string;
  children: ReactNode;
}) {
  const [position, setPosition] = useState<{ left: number; top: number } | null>(null);
  const drag = useRef<{ pointerId: number; offsetX: number; offsetY: number } | null>(null);

  function handlePointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    const popup = event.currentTarget.parentElement;
    if (!popup) return;
    const rect = popup.getBoundingClientRect();
    drag.current = {
      pointerId: event.pointerId,
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    setPosition({ left: rect.left, top: rect.top });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (drag.current?.pointerId !== event.pointerId) return;
    const popup = event.currentTarget.parentElement;
    if (!popup) return;
    const rect = popup.getBoundingClientRect();
    setPosition({
      left: Math.max(8, Math.min(event.clientX - drag.current.offsetX, window.innerWidth - rect.width - 8)),
      top: Math.max(8, Math.min(event.clientY - drag.current.offsetY, window.innerHeight - 48)),
    });
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    if (drag.current?.pointerId !== event.pointerId) return;
    drag.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  }

  return (
    <section
      className={className}
      style={position ? { left: position.left, top: position.top, right: 'auto', bottom: 'auto', transform: 'none' } : undefined}
      role="dialog"
      aria-modal="false"
      aria-label={label}
    >
      <div
        className="action-popup-drag-handle"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        ↕ 끌어서 이동
      </div>
      {children}
    </section>
  );
}

function scrollToGameBoard(id: string) {
  window.requestAnimationFrame(() => {
    const section = document.getElementById(id);
    if (!section) return;
    // The map reads as one picture, and the hex field itself does fit the viewport even though its
    // section (heading plus padding) does not — so center the board and let the heading scroll off.
    // Only the research board trades its top for its bottom, where its power-action row sits;
    // every other shortcut still lands on the section's top edge as before.
    const mapBoard = id === 'game-map' ? section.querySelector('.game-board-container') : null;
    const target = mapBoard ?? section;
    const hex = recentActionHex();
    scrollBoardIntoView(target, {
      behavior: 'smooth',
      preferred: mapBoard ? 'center' : 'start',
      allowBottomAlign: id === 'game-research',
      keepVisible: hex && target.contains(hex) ? hex : null,
    });
  });
}

/** Live play reuses the replay highlight markers to show what the last action touched. In replay
 * mode the surrounding `AiReplay` already provides its own value, which this must not override. */
function LiveHighlightScope({ highlight, enabled, children }: {
  highlight: ReturnType<typeof liveHighlight>;
  enabled: boolean;
  children: ReactNode;
}) {
  if (!enabled) return <>{children}</>;
  return (
    <ReplayHighlightContext.Provider value={highlight}>{children}</ReplayHighlightContext.Provider>
  );
}

function federationTokenKind(
  gameState: NonNullable<ReturnType<typeof useGameStore.getState>['gameState']>,
  choice: FederationTokenChoice,
): number | null {
  if (choice.source === 'Supply') return choice.kind;
  return gameState.spaceship_boards.find(({ id }) => id === choice.ship)?.federation_token ?? null;
}

export interface AppReplayControls {
  events: import('./types/game').GameEvent[];
  eventStart: number;
  eventEnd: number;
  onEventSelect: (index: number) => void;
}

export function App({ replay, sidePanel, coach }: { replay?: AppReplayControls; sidePanel?: ReactNode; coach?: CoachBoardControls } = {}) {
  const [view, setView] = useState<AppView>(replay ? 'game' : 'lobby');
  const [personalBoardPlayerId, setPersonalBoardPlayerId] = useState<number | null>(null);
  const [structurePopup, setStructurePopup] = useState<BoardStructurePopupState | null>(null);
  const [planetPopup, setPlanetPopup] = useState<BoardPlanetPopupState | null>(null);
  const [spaceshipPopup, setSpaceshipPopup] = useState<BoardSpaceshipPopupState | null>(null);
  const [techUpgradeFlow, setTechUpgradeFlow] = useState<TechUpgradeFlow | null>(null);
  const actionAnchorRef = useRef<Element | null>(null);
  const [rewardBatch, setRewardBatch] = useState<RewardBatch | null>(null);
  const rewardSequence = useRef(0);
  const rewardClick = useRef<{ x: number; y: number; time: number } | null>(null);
  const [sidebarTab, setSidebarTab] = useState<'info' | 'log'>('info');
  const [seenActionCount, setSeenActionCount] = useState(0);
  const [recentActionIndex, setRecentActionIndex] = useState<number | null>(null);
  const [tutorialOpen, setTutorialOpen] = useState(false);
  const [rangePreviewQic, setRangePreviewQic] = useState(0);
  const [gameNotice, setGameNotice] = useState<string | null>(null);
  const [suppressTerraformOreConfirmation, setSuppressTerraformOreConfirmation] = useState(false);
  const [devPowerChargeTargeting, setDevPowerChargeTargeting] = useState(false);
  const [boardArtifactId, setBoardArtifactId] = useState<number | null>(null);
  const [twilightRangeMode, setTwilightRangeMode] = useState(false);
  const [passBoosterSelection, setPassBoosterSelection] = useState(false);
  const [federationTokenChoice, setFederationTokenChoice] = useState<FederationTokenChoice | null>(null);
  const [replayFederationKind, setReplayFederationKind] = useState<number | null>(null);
  const [federationBonusCoord, setFederationBonusCoord] = useState<HexCoord | null>(null);
  const [federationBonusTechTile, setFederationBonusTechTile] = useState<number | null>(null);
  const [federationBonusResearchTrack, setFederationBonusResearchTrack] = useState<ResearchTrack | null>(null);
  const searchParams = new URLSearchParams(window.location.search);
  const savedManualControl = useRoomStore((s) => s.manualControl);
  const devGameRequested = !replay && (searchParams.get('devGame') === '1' || savedManualControl);

  const {
    roomCode,
    playerId,
    sessionToken,
    nickname,
    lastError,
    actions: roomActions,
  } = useRoomStore(
    (s) => ({
      roomCode: s.roomCode,
      playerId: s.playerId,
      sessionToken: s.sessionToken,
      nickname: s.nickname,
      lastError: s.lastError,
      actions: s.actions,
    }),
    shallow,
  );

  const {
    gameState,
    myPlayerId,
    activePlanet,
    selectedHexes,
    selectedAction,
    selectedPowerActionId,
    finalResult,
    wsClient, connectionReady, commandPending,
    actions: gameActions,
  } = useGameStore(
    (s) => ({
      gameState: s.gameState,
      myPlayerId: s.myPlayerId,
      activePlanet: s.activePlanet,
      selectedHexes: s.selectedHexes,
      selectedAction: s.selectedAction,
      selectedPowerActionId: s.selectedPowerActionId,
      finalResult: s.finalResult,
      wsClient: s.wsClient, connectionReady: s.connectionReady, commandPending: s.commandPending,
      actions: s.actions,
    }),
    shallow,
  );

  useEffect(() => {
    if (view !== 'game' || !gameState?.tutorial) return;
    closeBoardContext();
    setSidebarTab('info');
    setPersonalBoardPlayerId(null);
    setTutorialOpen(false);
    setPassBoosterSelection(false);
    setRangePreviewQic(0);
    const action = currentTutorialStep(gameState.tutorial)?.action;
    gameActions.selectAction(action?.type === 'FormFederation' ? 'FormFederation' : null);
    const panel = gameState.tutorial.step === 1 ? null : tutorialPanel(gameState);
    if (panel) {
      scrollToGameBoard(panel);
      window.requestAnimationFrame(() => {
        const board = document.getElementById(panel);
        const wanted = tutorialTargets(gameState);
        const primary = currentTutorialStep(gameState.tutorial!)?.target;
        const elements = Array.from(board?.querySelectorAll<HTMLElement>('[data-tutorial-target]') ?? []);
        const target = elements.find(node => node.dataset.tutorialTarget === primary)
          ?? elements.find(node => wanted.includes(node.dataset.tutorialTarget ?? ''));
        const focus = action?.type === 'ChargePower' ? target?.closest('.faction-board-main') : target;
        focus?.scrollIntoView?.({
          behavior: 'smooth',
          block: action?.type === 'ChargePower' ? 'start' : 'center',
          inline: 'nearest',
        });
      });
    }
  }, [gameState?.tutorial?.step, roomCode, view]);

  useEffect(() => {
    if (selectedAction !== 'TwilightReplayFederationToken' && selectedAction !== 'ExamineArtifact') {
      setReplayFederationKind(null);
    }
  }, [selectedAction]);


  useEffect(() => {
    if (replay || view !== 'game' || !roomCode || !sessionToken) return;

    const client = new GaiaWebSocket(roomCode);
    gameActions.setWsClient(client);

    let hasBaseline = false;
    const stopRewardConnection = client.onStateChange(() => { hasBaseline = false; setRewardBatch(null); });
    client.on((msg: ServerMessage) => {
      switch (msg.type) {
        case 'snapshot':
          roomActions.setRevision(msg.revision);
          if (isGameState(msg.state)) {
            const before = useGameStore.getState();
            const controlled = before.myPlayerId;
            const received = hasBaseline && controlled !== null
              ? resourceMotionBatch(before.gameState, msg.state, controlled) : null;
            if (received) {
              const click = rewardClick.current;
              setRewardBatch({ ...received, id: ++rewardSequence.current,
                origin: click && performance.now() - click.time < 2500 ? { x: click.x, y: click.y } : undefined });
            } else if (!hasBaseline || JSON.stringify((msg.state.event_log ?? []).slice(0, before.gameState?.event_log?.length ?? 0)) !== JSON.stringify(before.gameState?.event_log ?? [])) {
              setRewardBatch(null);
            }
            hasBaseline = true;
            gameActions.setGameState(msg.state);
          }
          break;
        case 'command_accepted':
          roomActions.setRevision(Math.max(useRoomStore.getState().revision, msg.revision));
          roomActions.setError(null);
          if (gameActions.acceptActionCommand(msg.command_id)) {
            closeBoardContext();
            setBoardArtifactId(null);
          }
          break;
        case 'command_rejected':
          roomActions.setRevision(Math.max(useRoomStore.getState().revision, msg.revision));
          gameActions.rejectActionCommand(msg.command_id);
          roomActions.setError({
            code: msg.rejection.code,
            message: msg.rejection.message_key,
          });
          break;
        case 'room_joined':
          gameActions.setMyPlayerId(msg.player_id);
          roomActions.setRevision(msg.revision);
          break;
        case 'error':
          roomActions.setError({ code: msg.code, message: msg.message });
          break;
        case 'game_ended':
          gameActions.setFinalResult({
            finalScores: msg.final_scores,
            winners: msg.winners,
          });
          break;
        default:
          break;
      }
    });

    client.connect();
    // Re-join on this fresh connection using the session established in the
    // lobby — `send` queues until the socket is open, no need to wait here.
    client.send({
      type: 'join_room',
      room_code: roomCode,
      nickname,
      session_token: sessionToken,
    });

    return () => {
      stopRewardConnection();
      client.disconnect();
      gameActions.setWsClient(null);
    };
  }, [view, roomCode, sessionToken, !!replay]);

  useEffect(() => {
    if (!replay && playerId !== null) {
      gameActions.setMyPlayerId(playerId);
    }
  }, [playerId]);

  useEffect(() => {
    if (gameState?.dev_controller == null) return;
    closeBoardContext();
    setPersonalBoardPlayerId(null);
    setPassBoosterSelection(false);
    setReplayFederationKind(null);
    setFederationTokenChoice(null);
    setRangePreviewQic(0);
  }, [myPlayerId]);

  useEffect(() => {
    if (!gameState || myPlayerId === null) return;
    const player = gameState.players.find(({ player_id }) => player_id === myPlayerId);
    if (player?.passed || gameState.round >= 6 || player?.booster == null) {
      setPassBoosterSelection(false);
    }
  }, [gameState, myPlayerId]);

  useEffect(() => {
    if (!gameState || myPlayerId === null || selectedAction !== 'FormFederation') {
      setFederationTokenChoice(null);
      return;
    }
    const selection = validateFederationSelection(gameState, myPlayerId, selectedHexes);
    if (!selection.valid) {
      setFederationTokenChoice(null);
      return;
    }
    scrollToGameBoard('game-federation-tokens');
  }, [gameState, myPlayerId, selectedAction, selectedHexes]);

  const handleGameStart = useCallback(() => {
    setView('game');
  }, []);

  // Debug-only coordinate picker for measuring image-relative slot
  // positions (see `CalibrationView`) — never linked to from in-game UI,
  // reached only by appending this query param by hand.
  if (!replay && searchParams.get('shuttlePreview') === '1') {
    return <ShuttlePreview />;
  }
  if (!replay && searchParams.get('calibrate') === '1') {
    return <CalibrationView />;
  }

  function handleReturnToLobby() {
    gameActions.reset();
    roomActions.reset();
    setView('lobby');
  }

  // Live activity: the log panel's own grouped entries, so the toast, the recent list, and the
  // board highlight all describe one action with the same wording. Replays keep their own feed.
  const actionEntries = useMemo(
    () => (replay ? [] : liveActionEntries(gameState?.event_log, gameState?.players ?? [], gameState?.board)),
    [replay, gameState?.event_log, gameState?.players, gameState?.board],
  );
  const latestActionIndex = actionEntries.length > 0
    ? actionEntries[actionEntries.length - 1].index
    : null;
  // A snapshot arrives with the whole game's history (join, refresh, reconnect). Only actions
  // that happen while watching are "just now" — the backlog must not toast or count as unread.
  const activitySynced = useRef(false);
  useEffect(() => {
    if (replay || latestActionIndex === null) return;
    if (!activitySynced.current) {
      activitySynced.current = true;
      setSeenActionCount(actionEntries.length);
      return;
    }
    setRecentActionIndex(latestActionIndex);
    const timer = window.setTimeout(() => setRecentActionIndex(null), 7000);
    return () => window.clearTimeout(timer);
  }, [replay, latestActionIndex, actionEntries.length]);
  useEffect(() => {
    if (sidebarTab === 'log') setSeenActionCount(actionEntries.length);
  }, [sidebarTab, actionEntries.length]);

  // Prefer the authoritative snapshot's own `Ended` phase over the one-time `game_ended`
  // broadcast in `finalResult` — a client that only ever loads a later snapshot (reconnect,
  // refresh, restart recovery) never sees that broadcast at all, but `gameState.phase` still
  // carries the same result since `RuleEngine::finalize_game` writes it into the engine state.
  const endedPhase =
    gameState && typeof gameState.phase === 'object' && 'Ended' in gameState.phase
      ? gameState.phase.Ended
      : null;
  const effectiveFinalResult: FinalResult | null = endedPhase
    ? { finalScores: endedPhase.final_scores, winners: endedPhase.winners }
    : finalResult;

  if (!replay && view === 'game' && effectiveFinalResult && gameState) {
    return (
      <GameOverScreen
        result={effectiveFinalResult}
        players={gameState.players}
        myPlayerId={myPlayerId ?? 0}
        onReturnToLobby={handleReturnToLobby}
      />
    );
  }

  if (view === 'lobby') {
    return (
      <div className="app app--lobby">
        <GameLobby onGameStart={handleGameStart} manualControl={devGameRequested} />
      </div>
    );
  }

  if (!gameState) {
    return (
      <div className="app app--loading">
        <div className="spinner" />
        <p>게임 상태를 불러오는 중...</p>
      </div>
    );
  }

  const myId = myPlayerId ?? 0;
  const me = gameState.players.find((p) => p.player_id === myId) ?? gameState.players[0];
  const orderedPlayers = [
    ...gameState.turn_order
      .map((id) => gameState.players.find((player) => player.player_id === id))
      .filter((player): player is NonNullable<typeof player> => player !== undefined),
    ...gameState.players.filter((player) => !gameState.turn_order.includes(player.player_id)),
  ];
  const factionBoardPlayers = [...gameState.players].sort((left, right) => {
    if (left.player_id === myId) return -1;
    if (right.player_id === myId) return 1;
    return left.player_id - right.player_id;
  });
  const personalBoardPlayer =
    personalBoardPlayerId === null
      ? null
      : (gameState.players.find((player) => player.player_id === personalBoardPlayerId) ?? null);
  const activePlayerId = activeActionPlayerId(gameState);
  const undoPending = gameState.undo_state?.pending_request ?? null;
  const commandBlocked = !replay && wsClient !== null && (!connectionReady || commandPending);
  const isMyActionTurn = !replay && !commandBlocked && activePlayerId === myId && undoPending === null;
  const hasServerFreeActions = gameState.undo_state?.open_turn?.player === myId
    && (gameState.undo_state.open_turn.free_action_revisions.length ?? 0) > 0;
  const usedPowerActions = gameState.used_power_actions;
  const lostPlanetPending =
    typeof gameState.phase === 'object' && 'LostPlanetPlacementPending' in gameState.phase
      ? gameState.phase.LostPlanetPlacementPending
      : null;
  const isMyLostPlanetPlacement = !replay && lostPlanetPending?.player === myId;
  const spaceshipHexes = new Set(Object.values(gameState.board.spaceship_tiles).map(({ q, r }) => `${q},${r}`));
  const lostPlanetTargets = isMyLostPlanetPlacement
    ? Object.values(gameState.board.hexes)
        .filter(
          (hex) =>
            hex.planet === null &&
            hex.structures.length === 0 &&
            hex.satellites.length === 0 &&
            !spaceshipHexes.has(`${hex.coord.q},${hex.coord.r}`),
        )
        .map((hex) => hex.coord)
    : [];
  const pendingDecisionPlayer = pendingDecisionPlayerId(gameState.phase);
  const latestAction = actionEntries[actionEntries.length - 1] ?? null;
  const toastAction = !replay && latestAction?.index === recentActionIndex ? latestAction : null;
  const activityHighlight = liveHighlight(gameState.event_log, toastAction);
  const unseenActions = replay ? 0 : Math.max(0, actionEntries.length - seenActionCount);
  const recentEntries = actionEntries.slice(-3).reverse();
  const turnBannerStatus = replay ? null : turnStatus(gameState, myId);
  const mainActionLocked =
    !!replay ||
    selectedAction !== null ||
    structurePopup !== null ||
    planetPopup !== null ||
    spaceshipPopup !== null ||
    techUpgradeFlow !== null;

  function handleResearchBoardAction(id: number) {
    if (!isMyActionTurn || usedPowerActions.includes(id)) return;
    if (
      mainActionLocked
      && (selectedAction !== 'PowerAction' || selectedPowerActionId !== id)
    ) return;
    if (id === 2 || id === 6) {
      if (selectedAction === 'PowerAction' && selectedPowerActionId === id) {
        gameActions.selectPowerAction(null);
        setPlanetPopup(null);
        return;
      }
      closeBoardContext();
      gameActions.selectPowerAction(id);
      return;
    }
    gameActions.sendAction({ type: 'PowerAction', id, coord: null });
  }

  function closeBoardContext() {
    setStructurePopup(null);
    setPlanetPopup(null);
    setSpaceshipPopup(null);
    setTechUpgradeFlow(null);
    setTwilightRangeMode(false);
  }

  function handleOwnedStructureClick(hex: Hex, anchor: { x: number; y: number }) {
    const structure = hex.structures.find(({ owner }) => owner === myId);
    if (!structure || !isMyActionTurn || mainActionLocked) return;
    gameActions.selectAction(null);
    setPlanetPopup(null);
    setSpaceshipPopup(null);
    setTechUpgradeFlow(null);
    setStructurePopup({ coord: hex.coord, structure: structure.kind, anchor });
  }

  function handlePlanetClick(hex: Hex, anchor: { x: number; y: number }) {
    const powerActionId = selectedAction === 'PowerAction'
      && (selectedPowerActionId === 2 || selectedPowerActionId === 6)
      ? selectedPowerActionId
      : undefined;
    if ((mainActionLocked && powerActionId === undefined)
      || (!devGameRequested && !gameState?.tutorial && powerActionId === undefined)
      || !hex.planet
      || hex.structures.length > 0
      || !isMyActionTurn) return;
    const occupiedByOther = hex.planet.owner !== null && !(hex.planet.owner === myId && hex.planet.is_gaia_formed);
    if (occupiedByOther) return;
    const rangeNotice = rangeRequirementNotice(
      informationCubesNeededForRange(gameState!.board, me, hex.coord),
      rangePreviewQic,
    );
    if (rangeNotice && !gameState?.tutorial) {
      setGameNotice(rangeNotice);
      return;
    }
    setGameNotice(null);
    if (powerActionId === undefined) gameActions.selectAction(null);
    setStructurePopup(null);
    setSpaceshipPopup(null);
    setTechUpgradeFlow(null);
    setPlanetPopup({ hex, anchor, powerActionId });
  }

  function handleSpaceshipClick(ship: SpaceshipId, anchor: { x: number; y: number }) {
    if (!isMyActionTurn || mainActionLocked) return;
    gameActions.selectAction(null);
    setGameNotice(null);
    setStructurePopup(null);
    setPlanetPopup(null);
    setTechUpgradeFlow(null);
    setSpaceshipPopup({ ship, anchor });
  }

  function handleArtifactClick(artifactId: number) {
    if (!isMyActionTurn || mainActionLocked) return;
    closeBoardContext();
    setGameNotice(null);
    if (artifactId === 10 && me.federation_tokens.length + (me.gray_federation_tokens?.length ?? 0) === 0) {
      cancelCurrentAction();
      setGameNotice('복사할 연방 토큰이 없습니다. 행동은 선택되지 않았습니다.');
      return;
    }
    setBoardArtifactId(artifactId);
    gameActions.selectAction('ExamineArtifact');
    if (artifactId === 10) {
      scrollToGameBoard('game-player-actions');
      return;
    }
    gameActions.sendAction({
      type: 'ExamineArtifact', artifact: artifactId, copy_federation_token_kind: null,
      bonus_build_coord: null, bonus_tech_tile: null, bonus_research_track: null,
    });
  }

  function replayAction(action: Extract<GameAction, { type: 'TwilightReplayFederationToken' }>): GameAction {
    return selectedAction === 'ExamineArtifact' && boardArtifactId === 10
      ? { type: 'ExamineArtifact', artifact: 10, copy_federation_token_kind: action.token_kind,
          bonus_build_coord: action.bonus_build_coord, bonus_tech_tile: action.bonus_tech_tile,
          bonus_research_track: action.bonus_research_track }
      : action;
  }

  function handleShipActionSelect(
    actionType: GameAction['type'],
    actionTypes: GameAction['type'][],
  ) {
    const reselectingCurrentSpace = selectedAction !== null && actionTypes.includes(selectedAction);
    if (!isMyActionTurn || (mainActionLocked && !reselectingCurrentSpace)) return;
    closeBoardContext();
    setBoardArtifactId(null);
    setReplayFederationKind(null);
    if (actionTypes.length > 1) {
      setTwilightRangeMode(true);
      routeShipAction(actionType, true);
      return;
    }
    routeShipAction(actionType);
  }

  function routeShipAction(actionType: GameAction['type'], preserveTwilightRange = false) {
    if (!preserveTwilightRange) setTwilightRangeMode(false);
    const prerequisiteNotice = shipActionPrerequisiteNotice(actionType, me, gameState!.board);
    if (prerequisiteNotice) {
      cancelCurrentAction();
      setGameNotice(`${prerequisiteNotice} 행동은 선택되지 않았습니다.`);
      return;
    }

    setGameNotice(null);
    gameActions.selectAction(actionType);

    if (IMMEDIATE_SPACESHIP_ACTIONS.has(actionType)) {
      if (actionType === 'RebellionCreditsAndQic') {
        gameActions.sendAction({ type: 'RebellionCreditsAndQic' });
      } else if (actionType === 'TFMarsTechBonus') {
        gameActions.sendAction({ type: 'TFMarsTechBonus' });
      } else if (actionType === 'EclipsePlanetTypeBonus') {
        gameActions.sendAction({ type: 'EclipsePlanetTypeBonus' });
      }
      return;
    }

    if (actionType === 'EclipseResearchBoost') {
      scrollToGameBoard('game-research');
      return;
    }

    if (actionType === 'RebellionGainTechTile') {
      setTechUpgradeFlow({
        stage: 'tile',
        coord: { q: 0, r: 0 },
        to: 'ResearchLab',
        anchor: { x: 12, y: 88 },
        completion: { kind: 'RebellionGainTechTile' },
      });
      scrollToGameBoard('game-research');
      return;
    }

    if (actionType === 'TwilightReplayFederationToken') {
      scrollToGameBoard('game-player-actions');
      return;
    }

    if (MAP_TARGET_SPACESHIP_ACTIONS.has(actionType)) {
      scrollToGameBoard('game-map');
    }
  }

  function previewBuild(hex: Hex, anchor: { x: number; y: number }, preview: BuildActionPreview) {
    if (!hex.planet || hex.planet.planet_type === 'Transdim' && !hex.planet.is_gaia_formed) {
      setGameNotice('광산을 건설할 행성을 선택하세요. 행동 선택은 유지됩니다.');
      return;
    }
    setPlanetPopup({ hex, anchor, buildAction: preview });
  }

  function handleSelectedShipActionHex(
    hex: Hex,
    anchor: { x: number; y: number },
  ): boolean {
    const replayBuild = (selectedAction === 'TwilightReplayFederationToken' || (selectedAction === 'ExamineArtifact' && boardArtifactId === 10))
      && (replayFederationKind === 14 || replayFederationKind === 15);
    if (!selectedAction || (!MAP_TARGET_SPACESHIP_ACTIONS.has(selectedAction) && !replayBuild)) {
      return false;
    }
    setGameNotice(null);

    if (replayBuild && replayFederationKind !== null) {
      previewBuild(hex, anchor, {
        action: replayAction({
          type: 'TwilightReplayFederationToken', token_kind: replayFederationKind,
          bonus_build_coord: hex.coord, bonus_tech_tile: null, bonus_research_track: null,
        }),
        waiveMineCost: true,
        unlimitedRange: replayFederationKind === 15,
        freeTerraformingSteps: replayFederationKind === 14 ? 3 : 0,
        extraQic: selectedAction === 'TwilightReplayFederationToken' ? 3 : 0,
      });
      return true;
    }

    if (twilightRangeMode || selectedAction === 'RoundBoosterRangeBuild' || selectedAction === 'GleensBuildMine') {
      const gleensRange = selectedAction === 'GleensBuildMine';
      const targetShip = Object.entries(gameState!.board.spaceship_tiles).find(([, coord]) =>
        coord?.q === hex.coord.q && coord.r === hex.coord.r,
      )?.[0] as SpaceshipId | undefined;
      if (targetShip) {
        gameActions.sendAction({ type: gleensRange ? 'GleensExploreSpaceship' : twilightRangeMode ? 'TwilightRangeExploreSpaceship' : 'RoundBoosterRangeExploreSpaceship', ship: targetShip });
      } else if (hex.planet?.planet_type === 'Transdim') {
        gameActions.sendAction({ type: gleensRange ? 'GleensGaiaFormation' : twilightRangeMode ? 'TwilightRangeGaiaFormation' : 'RoundBoosterRangeGaiaFormation', coord: hex.coord });
      } else if (hex.planet) {
        previewBuild(hex, anchor, {
          action: { type: gleensRange ? 'GleensBuildMine' : twilightRangeMode ? 'TwilightRangeBuild' : 'RoundBoosterRangeBuild', coord: hex.coord },
          rangeBonus: gleensRange ? 2 : 3, extraKnowledge: twilightRangeMode ? 1 : 0,
        });
      } else {
        setGameNotice('행성이나 탐사할 함선 칸을 선택하세요. 행동 선택은 유지됩니다.');
      }
      return true;
    }

    switch (selectedAction) {
      case 'RoundBoosterTerraformBuild':
        previewBuild(hex, anchor, { action: { type: 'RoundBoosterTerraformBuild', coord: hex.coord }, freeTerraformingSteps: 1 });
        return true;
      case 'SpaceGiantsBuildMine':
        previewBuild(hex, anchor, { action: { type: 'SpaceGiantsBuildMine', coord: hex.coord }, freeTerraformingSteps: 2 });
        return true;
      case 'RoundBoosterImmediateGaiaFormation':
        gameActions.sendAction({ type: 'RoundBoosterImmediateGaiaFormation', coord: hex.coord });
        return true;
      case 'TinkeroidsUseTile':
        if (me.tinkeroids_selected_tile != null) {
          previewBuild(hex, anchor, {
            action: { type: 'TinkeroidsUseTile', tile: me.tinkeroids_selected_tile, coord: hex.coord },
            freeTerraformingSteps: me.tinkeroids_selected_tile === 1 ? 1 : 3,
          });
        }
        return true;
      case 'TwilightFreeResearchLab': {
        const tradingStation = hex.structures.some(
          ({ owner, kind }) => owner === myId && kind === 'TradingStation',
        );
        if (!tradingStation) {
          setGameNotice('내 교역소를 선택하세요. 행동 선택은 유지됩니다.');
          return true;
        }
        if (selectableStandardTiles.length === 0 && selectableAdvancedTracks.length === 0) {
          gameActions.sendAction({
            type: 'TwilightFreeResearchLab',
            coord: hex.coord,
            tech_tile_choice: null,
          });
          return true;
        }
        setTechUpgradeFlow({
          stage: 'tile',
          coord: hex.coord,
          to: 'ResearchLab',
          anchor,
          completion: { kind: 'TwilightFreeResearchLab' },
        });
        scrollToGameBoard('game-research');
        return true;
      }
      case 'SpaceshipCreditTerraform':
        previewBuild(hex, anchor, { action: { type: 'SpaceshipCreditTerraform', coord: hex.coord }, freeTerraformingSteps: 1, extraCredits: 3 });
        return true;
      case 'TwilightRangeBuild':
        previewBuild(hex, anchor, { action: { type: 'TwilightRangeBuild', coord: hex.coord }, rangeBonus: 3, extraKnowledge: 1 });
        return true;
      case 'TwilightRangeGaiaFormation':
        gameActions.sendAction({ type: 'TwilightRangeGaiaFormation', coord: hex.coord });
        return true;
      case 'TwilightRangeExploreSpaceship': {
        const targetShip = Object.entries(gameState!.board.spaceship_tiles).find(([, coord]) =>
          coord?.q === hex.coord.q && coord.r === hex.coord.r,
        )?.[0] as SpaceshipId | undefined;
        if (!targetShip) {
          setGameNotice('탐사할 함선 칸을 선택하세요. 행동 선택은 유지됩니다.');
          return true;
        }
        gameActions.sendAction({ type: 'TwilightRangeExploreSpaceship', ship: targetShip });
        return true;
      }
      case 'RebellionFreeTradingStation':
        gameActions.sendAction({ type: 'RebellionFreeTradingStation', coord: hex.coord });
        return true;
      case 'TFMarsGaiaFormation':
        gameActions.sendAction({ type: 'TFMarsGaiaFormation', coord: hex.coord });
        return true;
      case 'EclipseAsteroidMine':
        previewBuild(hex, anchor, { action: { type: 'EclipseAsteroidMine', coord: hex.coord }, extraCredits: 6 });
        return true;
      default:
        return false;
    }
  }

  function handleUpgradeChoice(to: StructureType) {
    if (!structurePopup || !gameState) return;
    if (!canPayForUpgrade(me, gameState.board, structurePopup.coord, structurePopup.structure, to)) {
      return;
    }
    const grantsTechTile = to === 'ResearchLab' || typeof to === 'object'
      || (to === 'PlanetaryInstitute' && me?.faction === 'SpaceGiants' && !me.pi_ability_used);
    if (grantsTechTile) {
      if (selectableStandardTiles.length === 0 && selectableAdvancedTracks.length === 0) {
        gameActions.sendAction({
          type: 'Upgrade',
          coord: structurePopup.coord,
          to,
          tech_tile_choice: null,
        });
        return;
      }
      setTechUpgradeFlow({
        stage: 'tile',
        coord: structurePopup.coord,
        to,
        anchor: structurePopup.anchor,
        completion: { kind: 'Upgrade' },
      });
      setStructurePopup(null);
      scrollToGameBoard('game-research');
      return;
    }
    gameActions.sendAction({
      type: 'Upgrade',
      coord: structurePopup.coord,
      to,
      tech_tile_choice: null,
    });
  }

  function startFederationFromStructure() {
    if (!structurePopup) return;
    const coord = structurePopup.coord;
    closeBoardContext();
    setFederationTokenChoice(null);
    setFederationBonusCoord(null);
    setFederationBonusTechTile(null);
    setFederationBonusResearchTrack(null);
    gameActions.selectAction('FormFederation');
    gameActions.toggleHex(coord);
  }

  function sendTechUpgrade(choice: TechTileChoice) {
    if (!techUpgradeFlow) return;
    switch (techUpgradeFlow.completion.kind) {
      case 'TwilightFreeResearchLab':
        gameActions.sendAction({
          type: 'TwilightFreeResearchLab',
          coord: techUpgradeFlow.coord,
          tech_tile_choice: choice,
        });
        return;
      case 'RebellionGainTechTile':
        if (choice.kind !== 'Standard') return;
        gameActions.sendAction({
          type: 'RebellionGainTechTile',
          tile: choice.tile,
          track: choice.advance_track ?? RESEARCH_TRACK_ORDER[0],
          bonus_build_coord: choice.bonus_build_coord,
        });
        return;
      case 'TwilightReplayFederationToken':
        if (choice.kind !== 'Standard') return;
        gameActions.sendAction(replayAction({
          type: 'TwilightReplayFederationToken',
          token_kind: techUpgradeFlow.completion.tokenKind,
          bonus_build_coord: choice.bonus_build_coord,
          bonus_tech_tile: choice.tile,
          bonus_research_track: choice.advance_track,
        }));
        return;
      case 'FederationBonus':
        if (choice.kind !== 'Standard') return;
        setFederationBonusTechTile(choice.tile);
        setFederationBonusResearchTrack(choice.advance_track ?? null);
        setFederationBonusCoord(choice.bonus_build_coord ?? null);
        setTechUpgradeFlow(null);
        scrollToGameBoard('game-federation-tokens');
        return;
      case 'Upgrade':
        gameActions.sendAction({
          type: 'Upgrade',
          coord: techUpgradeFlow.coord,
          to: techUpgradeFlow.to,
          tech_tile_choice: choice,
        });
    }
  }

  function finishStandardTechChoice(tile: number, advanceTrack: ResearchTrack | null) {
    if (!techUpgradeFlow) return;
    if (tile === 11) {
      setTechUpgradeFlow({
        ...techUpgradeFlow,
        stage: 'bonus-mine',
        tile,
        advanceTrack,
      });
      return;
    }
    sendTechUpgrade({
      kind: 'Standard',
      tile,
      advance_track: advanceTrack,
      bonus_build_coord: null,
    });
  }

  function handleStandardTechTile(tile: number, slotIndex: number) {
    if (techUpgradeFlow?.stage !== 'tile') return;
    const alignedTrack = RESEARCH_TRACK_ORDER[slotIndex];
    if (alignedTrack) {
      finishStandardTechChoice(tile, alignedTrack);
      return;
    }
    if (selectableTechResearchTracks.length === 0) {
      finishStandardTechChoice(tile, null);
      return;
    }
    setTechUpgradeFlow({ ...techUpgradeFlow, stage: 'track', tile });
  }

  function handleTechResearchTrack(track: ResearchTrack) {
    if (selectedAction === 'BescodsLowestResearchAdvance') {
      if (!isMyActionTurn || !selectableBescodsResearchTracks.includes(track)) return;
      gameActions.sendAction({ type: 'BescodsLowestResearchAdvance', track });
    } else if (selectedAction === 'EclipseResearchBoost') {
      gameActions.sendAction({ type: 'EclipseResearchBoost', track });
    } else if (techUpgradeFlow?.stage === 'track') {
      finishStandardTechChoice(techUpgradeFlow.tile, track);
    } else if (techUpgradeFlow?.stage === 'advanced-track') {
      sendTechUpgrade({
        ...(techUpgradeFlow.lostFleet ? { kind: 'LostFleetAdvanced' as const } : { kind: 'Advanced' as const, track: techUpgradeFlow.track }),
        covered_tile: techUpgradeFlow.coveredTile,
        advance_track: track,
      });
    }
  }

  function handlePaidResearchTrack(track: ResearchTrack) {
    if (!isMyActionTurn || me.resources.knowledge < 4) return;
    gameActions.sendAction({ type: 'ResearchAdvance', track });
  }

  function handleAdvancedTechTile(tile: number, track: ResearchTrack) {
    if (techUpgradeFlow?.stage !== 'tile') return;
    setTechUpgradeFlow({ ...techUpgradeFlow, stage: 'cover', tile, track });
  }

  function handleCoveredTechTile(tile: number) {
    if (techUpgradeFlow?.stage !== 'cover') return;
    if (selectableAdvancedTechResearchTracks.length === 0) {
      sendTechUpgrade({
        ...(techUpgradeFlow.lostFleet ? { kind: 'LostFleetAdvanced' as const } : { kind: 'Advanced' as const, track: techUpgradeFlow.track }),
        covered_tile: tile,
        advance_track: null,
      });
      return;
    }
    setTechUpgradeFlow({ ...techUpgradeFlow, stage: 'advanced-track', coveredTile: tile });
  }

  function finishUpgradeWithoutResearchAdvance() {
    if (techUpgradeFlow?.stage === 'track') {
      finishStandardTechChoice(techUpgradeFlow.tile, null);
    } else if (techUpgradeFlow?.stage === 'advanced-track') {
      sendTechUpgrade({
        ...(techUpgradeFlow.lostFleet ? { kind: 'LostFleetAdvanced' as const } : { kind: 'Advanced' as const, track: techUpgradeFlow.track }),
        covered_tile: techUpgradeFlow.coveredTile,
        advance_track: null,
      });
    }
  }

  function handleBonusMineTarget(coord: HexCoord) {
    if (techUpgradeFlow?.stage !== 'bonus-mine') return;
    sendTechUpgrade({
      kind: 'Standard',
      tile: techUpgradeFlow.tile,
      advance_track: techUpgradeFlow.advanceTrack,
      bonus_build_coord: coord,
    });
  }

  function handleReplayFederationKind(kind: number) {
    setReplayFederationKind(kind);
    if (kind === 12) {
      if (selectableStandardTiles.length === 0) {
        gameActions.sendAction(replayAction({
          type: 'TwilightReplayFederationToken',
          token_kind: kind,
          bonus_build_coord: null,
          bonus_tech_tile: null,
          bonus_research_track: null,
        }));
        return;
      }
      setTechUpgradeFlow({
        stage: 'tile',
        coord: { q: 0, r: 0 },
        to: 'ResearchLab',
        anchor: { x: 12, y: 88 },
        completion: { kind: 'TwilightReplayFederationToken', tokenKind: kind },
      });
      scrollToGameBoard('game-research');
      return;
    }
    if (kind === 14 || kind === 15) {
      scrollToGameBoard('game-map');
      return;
    }
    gameActions.sendAction(replayAction({
      type: 'TwilightReplayFederationToken',
      token_kind: kind,
      bonus_build_coord: null,
      bonus_tech_tile: null,
      bonus_research_track: null,
    }));
  }

  function cancelCurrentAction() {
    gameActions.selectAction(null);
    closeBoardContext();
    setRangePreviewQic(0);
    setPassBoosterSelection(false);
    setBoardArtifactId(null);
    setReplayFederationKind(null);
    setFederationTokenChoice(null);
    setFederationBonusCoord(null);
    setFederationBonusTechTile(null);
    setFederationBonusResearchTrack(null);
    setGameNotice(null);
  }

  const ownedUncoveredTechTiles = (me.tech_tiles ?? []).filter((tile) => !(me.covered_tech_tiles ?? []).includes(tile));
  const selectableResearchBoardTechTiles = (gameState.research_board.tech_tile_slots ?? []).filter(
    (tile): tile is number => tile !== null && !(me.tech_tiles ?? []).includes(tile),
  );
  const exploredShipIndexes = new Set(me.explored_ships ?? []);
  const spaceshipIndex: Record<SpaceshipId, number> = {
    Twilight: 0,
    Rebellion: 1,
    TFMars: 2,
    Eclipse: 3,
  };
  const selectableSpaceshipTechTiles = gameState.spaceship_boards
    .filter((board) =>
      board.explorers.includes(myId) || exploredShipIndexes.has(spaceshipIndex[board.id]),
    )
    .flatMap((board) => board.tech_tiles ?? [])
    .filter((tile) => !(me.tech_tiles ?? []).includes(tile));
  const selectableStandardTiles = [
    ...new Set([...selectableResearchBoardTechTiles, ...selectableSpaceshipTechTiles]),
  ];
  const greenFederationTokenCount = me.federation_tokens.length;
  const selectableAdvancedTracks =
    greenFederationTokenCount > 0 && ownedUncoveredTechTiles.length > 0
      ? RESEARCH_TRACK_ORDER.filter((track, index) =>
          researchLevel(me, track) >= 4
          && gameState.research_board.advanced_tech_tiles[index] !== null,
        )
      : [];
  const selectableResearchTracksForTech = (advancedTile: boolean) => RESEARCH_TRACK_ORDER.filter((track) => {
    const level = researchLevel(me, track);
    if (level >= 5) return false;
    if (me.faction === 'BalTaks'
      && track === 'Navigation'
      && !me.structures.some(({ kind }) => kind === 'PlanetaryInstitute')) return false;
    if (level < 4) return true;
    const requiredGreenTokens = advancedTile ? 2 : 1;
    return greenFederationTokenCount >= requiredGreenTokens
      && !gameState.players.some((player) => player.player_id !== myId && researchLevel(player, track) >= 5);
  });
  const selectableStandardTechResearchTracks = selectableResearchTracksForTech(false);
  const selectableAdvancedTechResearchTracks = selectableResearchTracksForTech(true);
  const lowestBescodsLevel = Math.min(...RESEARCH_TRACK_ORDER.map((track) => researchLevel(me, track)));
  const selectableBescodsResearchTracks = selectableStandardTechResearchTracks.filter(
    (track) => researchLevel(me, track) === lowestBescodsLevel,
  );
  const selectableTechResearchTracks = techUpgradeFlow?.stage === 'advanced-track'
    ? selectableAdvancedTechResearchTracks
    : selectableStandardTechResearchTracks;
  const bonusMineTargets =
    techUpgradeFlow?.stage === 'bonus-mine' ? Object.values(gameState.board.hexes).map((hex) => hex.coord) : [];
  const federationSelectableHexes = selectedAction === 'FormFederation'
    ? selectableFederationHexes(gameState, myId, selectedHexes)
    : [];
  const federationSelection = selectedAction === 'FormFederation'
    ? validateFederationSelection(gameState, myId, selectedHexes)
    : null;

  function handleFederationTokenChoice(choice: FederationTokenChoice) {
    setFederationTokenChoice(choice);
    setFederationBonusCoord(null);
    setFederationBonusTechTile(null);
    setFederationBonusResearchTrack(null);

    if (federationTokenKind(gameState!, choice) !== 12) {
      if (techUpgradeFlow?.completion.kind === 'FederationBonus') setTechUpgradeFlow(null);
      return;
    }

    if (selectableStandardTiles.length === 0) {
      setTechUpgradeFlow(null);
      scrollToGameBoard('game-federation-tokens');
      return;
    }

    const anchorCoord = selectedHexes[0] ?? { q: 0, r: 0 };
    setTechUpgradeFlow({
      stage: 'tile',
      coord: anchorCoord,
      to: 'ResearchLab',
      anchor: { x: 12, y: 88 },
      completion: { kind: 'FederationBonus' },
    });
    scrollToGameBoard('game-research');
  }

  const availableSpaceshipFederationTokens = gameState.spaceship_boards
    .filter((board) =>
      (board.explorers.includes(myId) || exploredShipIndexes.has(spaceshipIndex[board.id]))
      && board.federation_token !== null,
    )
    .map((board) => ({ ship: board.id, kind: board.federation_token as number }));
  const selectedTerraformingPowerAction = selectedAction === 'PowerAction'
    && (selectedPowerActionId === 2 || selectedPowerActionId === 6);
  const popupState = structurePopup ?? techUpgradeFlow;
  let popupMode: StructurePopupMode | null = null;
  if (structurePopup) {
    popupMode = {
      kind: 'structure',
      structure: structurePopup.structure,
      faction: me.faction,
    };
  } else if (techUpgradeFlow?.stage === 'tile') {
    popupMode = { kind: 'choose-tech' };
  } else if (techUpgradeFlow?.stage === 'track' || techUpgradeFlow?.stage === 'advanced-track') {
    popupMode = { kind: 'choose-track' };
  } else if (techUpgradeFlow?.stage === 'bonus-mine') {
    popupMode = { kind: 'choose-bonus-mine' };
  } else if (techUpgradeFlow?.stage === 'cover') {
    popupMode = { kind: 'choose-cover', tileIds: ownedUncoveredTechTiles };
  }

  return (
    <LiveHighlightScope highlight={activityHighlight} enabled={!replay}>
    <div className={`app app--game app--game-table${gameState.tutorial ? ' app--tutorial' : ''}`} onClickCapture={(event) => {
      const target = event.target;
      if (gameState.tutorial && target instanceof Element) {
        const marked = target.closest<HTMLElement>('[data-tutorial-target]');
        if (marked && !tutorialTargets(gameState).includes(marked.dataset.tutorialTarget ?? '')) {
          event.preventDefault();
          event.stopPropagation();
          roomActions.setError({ code: 'TutorialStepMismatch', message: tutorialNotice(gameState.tutorial) });
          return;
        }
      }
      if (!replay && target instanceof Element && target.closest('button, [role="button"]')) {
        const bounds = target.closest('button, [role="button"]')!.getBoundingClientRect();
        rewardClick.current = { x: bounds.left + bounds.width / 2, y: bounds.top + bounds.height / 2, time: performance.now() };
      }
      if (target instanceof Element && target.closest('.game-table-scroll, .structure-action-popup')) {
        actionAnchorRef.current = target.closest('button, [role="button"]') ?? target;
      }
    }}>
      {!replay && <RewardMotion batch={rewardBatch} />}
      {!replay && <TurnBanner status={turnBannerStatus} />}
      {!replay && <ActionToast entry={toastAction} myPlayerId={myId} />}
      {!replay && (lastError || gameNotice) && (
        <div
          className="error-banner"
          role="status"
          onClick={() => {
            roomActions.setError(null);
            setGameNotice(null);
          }}
        >
          {lastError ? `${lastError.message} (${lastError.code})` : gameNotice}
        </div>
      )}
      <nav className="game-section-nav game-table-top-nav" aria-label="보드 바로가기">
        {/* Plain anchors would jump with the browser's own top alignment, which cuts the bottom
            of a board taller than the viewport — `scrollToGameBoard` applies this app's rule. */}
        {([
          ['game-overview', '목표·부스터'],
          ['game-map', '우주'],
          ['game-research', '연구·함선'],
          ['game-factions', '종족'],
        ] as const).map(([id, label]) => (
          <a
            key={id}
            href={`#${id}`}
            onClick={(event) => {
              event.preventDefault();
              scrollToGameBoard(id);
            }}
          >
            {label}
          </a>
        ))}
        <div className="game-table-top-actions">
          {!replay && wsClient && <GameCommandStatus ready={connectionReady} pending={commandPending} />}
          {/* The same reference the lobby's 튜토리얼 page shows, as a pinned panel so the board
              stays usable while reading it. */}
          {!replay && (
            <button type="button" className="game-table-help-button" onClick={() => setTutorialOpen(true)}>
              도움말
            </button>
          )}
          {!replay && savedManualControl && <DevTestControls refillDisabled={mainActionLocked || !isMyActionTurn} />}
          <TopPassControl
            player={me}
            round={gameState.round}
            availableBoosters={gameState.boosters}
            isMyTurn={coach ? coach.enabled : isMyActionTurn && !mainActionLocked}
            onChooseBooster={() => {
              setPassBoosterSelection(true);
              scrollToGameBoard('game-round-boosters');
            }}
            onPass={(boosterId) => {
              if (coach) { coach.onAction({ type: 'Pass', booster_id: boosterId }); return; }
              setPassBoosterSelection(false);
              gameActions.sendAction({ type: 'Pass', booster_id: boosterId });
            }}
          />
        </div>
      </nav>
      <GameCommandControls blocked={commandBlocked}>
      <main className="game-table-scroll">
        <section className="game-table-section game-table-overview" id="game-overview">
          <article className="game-table-card game-table-scoring-card">
            <h2>라운드·게임 종료 목표</h2>
            <ScoringBoard
              roundTiles={gameState.round_tiles}
              finalScoringTiles={gameState.final_scoring_tiles}
              currentRound={gameState.round}
              gameState={gameState}
            />
          </article>
          <article
            className={`game-table-card game-table-boosters-card${
              passBoosterSelection ? ' game-table-card--awaiting-selection' : ''
            }`}
            id="game-round-boosters"
          >
            <h2>라운드 부스터</h2>
            <RoundBoosters
              availableBoosters={gameState.boosters}
              players={gameState.players}
              selectionMode={coach ? coach.enabled && coach.boosterSelection : passBoosterSelection}
              onSelectBooster={(boosterId) => {
                if (coach) { coach.onAction({ booster_id: boosterId }); return; }
                setPassBoosterSelection(false);
                gameActions.sendAction({ type: 'Pass', booster_id: boosterId });
              }}
            />
          </article>
          <article
            className={`game-table-card game-table-federation-card${
              federationSelection?.valid ? ' game-table-card--awaiting-selection' : ''
            }`}
            id="game-federation-tokens"
          >
            <h2>연방 토큰</h2>
            <FederationTokens
              availableTokens={gameState.research_board.federation_tokens}
              players={gameState.players}
              selectionMode={coach ? coach.enabled && coach.federationSelection : federationSelection?.valid ?? false}
              selectedToken={federationTokenChoice}
              spaceshipTokens={availableSpaceshipFederationTokens}
              onSelectToken={coach ? token => coach.onAction({ type: 'FormFederation', token }) : handleFederationTokenChoice}
              showHoldings={false}
            />
          </article>
          <article className="game-table-card game-table-terraforming-card">
            <h2>테라포밍 색상</h2>
            <TerraformingSelectionBoard
              colorOrder={gameState.terraforming_color_order ?? []}
              allocations={gameState.players.flatMap((player) =>
                (player.faction === 'Moweyds' || player.faction === 'Tinkeroids') && player.expensive_terraforming_planet_types?.length
                  ? [{ faction: player.faction, colors: player.expensive_terraforming_planet_types }]
                  : []
              )}
            />
          </article>
        </section>

        <section className="game-table-section game-table-map" id="game-map" aria-label="우주 섹터 보드">
          <header className="game-table-section-heading">
            <h2>우주 섹터 보드</h2>
          </header>
          <GameBoard
            board={gameState.board}
            tutorialChargeCue={gameState.tutorial?.step === 3}
            players={gameState.players}
            validTargets={coach ? coach.targets : isMyLostPlanetPlacement ? lostPlanetTargets : bonusMineTargets}
            federationSelectableHexes={federationSelectableHexes}
            selectedCoord={isMyLostPlanetPlacement ? activePlanet : null}
            onHexClick={
              coach ? coach.onHex : isMyLostPlanetPlacement
                ? gameActions.selectPlanet
                : techUpgradeFlow?.stage === 'bonus-mine'
                  ? handleBonusMineTarget
                  : undefined
            }
            interactivePlayerId={isMyActionTurn ? myId : undefined}
            onOwnedStructureClick={
              isMyActionTurn && !mainActionLocked ? handleOwnedStructureClick : undefined
            }
            onPlanetClick={
              isMyActionTurn && (devGameRequested || !!gameState.tutorial || selectedTerraformingPowerAction)
                ? handlePlanetClick
                : undefined
            }
            onSpaceshipClick={
              isMyActionTurn && !mainActionLocked ? handleSpaceshipClick : undefined
            }
            onSelectedActionHexClick={handleSelectedShipActionHex}
            allowPlanetPopupDuringSelectedAction={selectedTerraformingPowerAction}
            devPowerChargeTargeting={devPowerChargeTargeting}
            onPowerChargeStructureClick={(hex) => {
              gameActions.triggerDevPowerCharge(hex.coord);
              setDevPowerChargeTargeting(false);
              closeBoardContext();
            }}
            onContextDismiss={closeBoardContext}
            emphasizeStructures={devGameRequested}
            rangePlayerId={devGameRequested || twilightRangeMode || selectedAction === 'RoundBoosterRangeBuild' || selectedAction === 'GleensBuildMine' ? myId : undefined}
            rangePreviewBonus={rangePreviewQic * 2 + (selectedAction === 'GleensBuildMine' ? 2 : twilightRangeMode || selectedAction === 'RoundBoosterRangeBuild' ? 3 : 0)}
          />
        </section>

        <section className="game-table-section game-table-research-row" id="game-research-section">
          <article className="game-table-card game-table-tech-requirement-card">
            <h2>고급 기술 조건</h2>
            <div className="game-table-tech-requirement">
              <LostFleetTechRequirementBoard
                side={gameState.research_board.lost_fleet_advanced_tech_requirement}
                tileId={gameState.research_board.lost_fleet_advanced_tech_tile}
                onSelect={coach?.enabled && coach.techMode && gameState.research_board.lost_fleet_advanced_tech_tile != null
                  && coach.advancedTiles.includes(gameState.research_board.lost_fleet_advanced_tech_tile)
                  ? () => coach.onTech(gameState.research_board.lost_fleet_advanced_tech_tile!, true)
                  : gameState.tutorial && techUpgradeFlow?.stage === 'tile' && gameState.research_board.lost_fleet_advanced_tech_tile != null
                    ? () => setTechUpgradeFlow({ ...techUpgradeFlow, stage: 'cover', tile: gameState.research_board.lost_fleet_advanced_tech_tile!, track: 'Science', lostFleet: true })
                    : undefined}
              />
            </div>
          </article>
          <article className={`game-table-card game-table-research-card${selectedAction === 'BescodsLowestResearchAdvance' ? ' is-bescods-research' : ''}`} id="game-research">
            <h2>연구 트랙</h2>
            <ResearchBoard
              players={gameState.players}
              board={gameState.research_board}
              usedPowerActions={gameState.used_power_actions}
              isMyTurn={coach ? coach.enabled : isMyActionTurn}
              mainActionLocked={coach ? !coach.enabled : mainActionLocked}
              selectedPowerActionId={selectedPowerActionId}
              allowTechReselection={!!coach?.enabled && coach.techMode !== null}
              onPowerAction={coach ? id => coach.onAction({ type: 'PowerAction', id }) : handleResearchBoardAction}
              techSelectionMode={
                coach ? coach.techMode : techUpgradeFlow?.stage === 'tile'
                  ? 'tile'
                  : techUpgradeFlow?.stage === 'track' || (!!gameState.tutorial && techUpgradeFlow?.stage === 'advanced-track') || selectedAction === 'EclipseResearchBoost' || selectedAction === 'BescodsLowestResearchAdvance'
                    ? 'track'
                    : null
              }
              selectableStandardTiles={coach ? coach.standardTiles : selectableStandardTiles}
              selectableAdvancedTracks={coach ? coach.advancedTracks : selectableAdvancedTracks}
              selectableResearchTracks={coach ? coach.researchTracks : selectedAction === 'BescodsLowestResearchAdvance' ? selectableBescodsResearchTracks : selectableTechResearchTracks}
              onStandardTechTile={coach ? tile => coach.onTech(tile) : handleStandardTechTile}
              onAdvancedTechTile={coach ? tile => coach.onTech(tile, true) : handleAdvancedTechTile}
              onResearchTrack={coach ? coach.onTrack : handleTechResearchTrack}
              onPaidResearchTrack={
                coach ? coach.enabled ? coach.onTrack : undefined : !mainActionLocked && isMyActionTurn ? handlePaidResearchTrack : undefined
              }
            />
          </article>
          <PlayerActionShelf
            id="game-player-actions"
            player={me}
            isMyTurn={coach ? coach.enabled : isMyActionTurn}
            mainActionLocked={coach ? !coach.enabled : mainActionLocked}
            federationSelectionMode={selectedAction === 'TwilightReplayFederationToken' || (selectedAction === 'ExamineArtifact' && boardArtifactId === 10)}
            selectedFederationKind={replayFederationKind}
            onSelectFederationKind={handleReplayFederationKind}
            onSelectBoosterAction={(booster) => {
              if (coach) { coach.onTypes(booster === 5 ? ['RoundBoosterImmediateGaiaFormation'] : booster === 12 ? ['RoundBoosterTerraformBuild'] : ['RoundBoosterRangeBuild', 'RoundBoosterRangeGaiaFormation', 'RoundBoosterRangeExploreSpaceship']); return; }
              if (!isMyActionTurn || mainActionLocked) return;
              closeBoardContext();
              setGameNotice(null);
              gameActions.selectAction(booster === 5 ? 'RoundBoosterImmediateGaiaFormation' : booster === 12 ? 'RoundBoosterTerraformBuild' : 'RoundBoosterRangeBuild');
              scrollToGameBoard('game-map');
            }}
            onSelectExplorationAction={(action) => {
              if (coach) { coach.onTypes([action]); return; }
              if (!isMyActionTurn || mainActionLocked) return;
              closeBoardContext();
              setGameNotice(null);
              gameActions.selectAction(action);
              scrollToGameBoard('game-map');
            }}
            onSelectFactionAction={(action) => {
              if (coach) { coach.onTypes([action]); return; }
              if (!isMyActionTurn || mainActionLocked) return;
              closeBoardContext();
              setGameNotice(null);
              gameActions.selectAction(action);
              scrollToGameBoard('game-map');
            }}
            onSelectBescodsResearch={() => {
              if (coach) { coach.onTypes(['BescodsLowestResearchAdvance']); return; }
              if (!isMyActionTurn || mainActionLocked) return;
              closeBoardContext();
              setGameNotice(null);
              gameActions.selectAction('BescodsLowestResearchAdvance');
              scrollToGameBoard('game-research');
            }}
            onSelectTinkeringTile={() => {
              if (coach) { coach.onTypes(['TinkeroidsUseTile']); return; }
              if (!isMyActionTurn || mainActionLocked) return;
              closeBoardContext();
              gameActions.selectAction('TinkeroidsUseTile');
              scrollToGameBoard('game-map');
            }}
            onAction={coach ? coach.onAction : gameActions.sendAction}
          />
          <article className="game-table-card game-table-ships-card" id="game-ships">
            <h2>함선 보드</h2>
            <SpaceshipBoards
              spaceshipBoards={gameState.spaceship_boards}
              players={gameState.players}
              myPlayerId={myId}
              isMyTurn={coach ? coach.enabled : isMyActionTurn}
              mainActionLocked={coach ? !coach.enabled : mainActionLocked}
              usedActionIds={gameState.used_spaceship_actions}
              selectedAction={selectedAction}
              selectableTechTiles={coach ? coach.standardTiles : techUpgradeFlow?.stage === 'tile' ? selectableStandardTiles : []}
              onActionSelect={coach ? (_, types) => coach.onTypes(types) : handleShipActionSelect}
              onArtifactSelect={coach ? artifact => coach.onAction({ type: 'ExamineArtifact', artifact }) : handleArtifactClick}
              onTechTileSelect={
                coach ? tile => coach.onTech(tile) : techUpgradeFlow?.stage === 'tile'
                  ? (tile) => handleStandardTechTile(tile, -1)
                  : undefined
              }
            />
          </article>
        </section>

        <section className="game-table-section" id="game-factions">
          <header className="game-table-section-heading">
            <h2>종족 보드</h2>
          </header>
          <div className="game-table-player-grid">
            {factionBoardPlayers.map((player) => (
              <article
                key={player.player_id}
                data-replay-player={replay ? player.player_id : undefined}
                className={`game-table-player-card${player.player_id === myId ? ' game-table-player-card--me' : ''}`}
              >
                <header>
                  <strong
                    className="game-table-player-name"
                    style={{
                      color: player.faction
                        ? STRUCTURE_COLOR_HEX[FACTION_STRUCTURE_COLOR[player.faction]]
                        : '#cbd5e1',
                    }}
                  >
                    {player.nickname}
                  </strong>
                  <span>{factionDisplayName(player.faction)}</span>
                  <b>{player.vp}점</b>
                </header>
                <PlayerDashboard player={player} />
              </article>
            ))}
          </div>
        </section>
      </main>
      </GameCommandControls>
      <aside className={`game-sidebar${gameState.tutorial ? ' game-sidebar--tutorial' : ''}`}>
        {!replay && gameState.tutorial && <RoundOneGuide key={roomCode} state={gameState} />}
        {sidePanel ?? <>
        <div className="game-sidebar-tabs" role="tablist" aria-label="오른쪽 패널">
          <button
            type="button"
            role="tab"
            id="game-sidebar-info-tab"
            aria-controls="game-sidebar-info-panel"
            aria-selected={sidebarTab === 'info'}
            className={sidebarTab === 'info' ? 'is-active' : undefined}
            onClick={() => setSidebarTab('info')}
          >
            정보
          </button>
          <button
            type="button"
            role="tab"
            id="game-sidebar-log-tab"
            aria-controls="game-sidebar-log-panel"
            aria-selected={sidebarTab === 'log'}
            className={sidebarTab === 'log' ? 'is-active' : undefined}
            onClick={() => setSidebarTab('log')}
          >
            로그
            {unseenActions > 0 && (
              <span className="game-sidebar-unread" aria-label={`읽지 않은 기록 ${unseenActions}개`}>
                {unseenActions}
              </span>
            )}
          </button>
        </div>
        {sidebarTab === 'info' ? (
          <div
            className="game-sidebar-tab-panel game-sidebar-tab-panel--info"
            id="game-sidebar-info-panel"
            role="tabpanel"
            aria-labelledby="game-sidebar-info-tab"
          >
            <RecentActions entries={recentEntries} onOpenLog={() => setSidebarTab('log')} />
            <OpponentPanels
              players={orderedPlayers}
              myPlayerId={myId}
              activePlayerId={activePlayerId}
              events={gameState.event_log ?? []}
              round={gameState.round}
              economyResearchTileSide={gameState.research_board.economy_research_tile_side}
              onPlayerSelect={(player) => setPersonalBoardPlayerId(player.player_id)}
            />
            <GameCommandControls blocked={commandBlocked}>
            <SidebarTurnControls
              player={me}
              isMyTurn={coach ? coach.enabled : isMyActionTurn}
              onFreeAction={(kind) => {
                const expected = gameState.tutorial && currentTutorialStep(gameState.tutorial)?.action;
                const count = expected?.type === 'FreeAction' && expected.kind === kind ? expected.count : 1;
                gameActions.sendAction({ type: 'FreeAction', kind, count });
              }}
              rangePreviewQic={rangePreviewQic}
              onRangePreviewAdd={() => {
                setGameNotice(null);
                setRangePreviewQic((current) => Math.min(current + 1, me.resources.qic));
              }}
              showDevPowerChargeTest={!replay && devGameRequested}
              devPowerChargeTargeting={devPowerChargeTargeting}
              onDevPowerChargeToggle={() => {
                closeBoardContext();
                setDevPowerChargeTargeting((active) => !active);
              }}
              undoState={gameState.undo_state}
              immediateTurnUndo={gameState.dev_controller != null && gameState.dev_controller === playerId}
              players={gameState.players}
              onUndoFreeAction={() => {
                setRangePreviewQic(0);
                setGameNotice(null);
                if (hasServerFreeActions) gameActions.undoFreeAction();
              }}
              onRequestTurnUndo={gameActions.requestTurnUndo}
              onRespondTurnUndo={gameActions.respondTurnUndo}
            />
            </GameCommandControls>
          </div>
        ) : (
          <div
            className="game-sidebar-tab-panel game-sidebar-tab-panel--log"
            id="game-sidebar-log-panel"
            role="tabpanel"
            aria-labelledby="game-sidebar-log-tab"
          >
            <GameLog events={replay?.events ?? gameState.event_log ?? []} players={gameState.players} board={gameState.board}
              onEventSelect={replay?.onEventSelect} activeEventRange={replay ? [replay.eventStart, replay.eventEnd] : undefined} />
          </div>
        )}
        </>}
      </aside>
      <GameCommandControls blocked={commandBlocked}>
      {!replay && mainActionLocked && (
        <ActionCancelButton anchor={selectedAction === 'BescodsLowestResearchAdvance' ? document.getElementById('game-research') : actionAnchorRef.current} onCancel={cancelCurrentAction} />
      )}
      {popupState && popupMode && (
        <StructureActionPopup
          anchor={popupState.anchor}
          coord={popupState.coord}
          mode={popupMode}
          onUpgrade={handleUpgradeChoice}
          onStartFederation={startFederationFromStructure}
          onCoverTile={handleCoveredTechTile}
          onSkipResearch={finishUpgradeWithoutResearchAdvance}
          player={me}
          board={gameState.board}
          onClose={closeBoardContext}
        />
      )}
      {planetPopup && (
        <PlanetActionPopup
          key={`${planetPopup.hex.coord.q},${planetPopup.hex.coord.r}:${planetPopup.buildAction?.action.type ?? "Build"}`}
          buildAction={planetPopup.buildAction}
          anchor={planetPopup.anchor}
          hex={planetPopup.hex}
          player={me}
          players={gameState.players}
          board={gameState.board}
          powerAction={planetPopup.powerActionId === undefined ? undefined : {
            id: planetPopup.powerActionId,
            freeTerraformingSteps: planetPopup.powerActionId === 2 ? 2 : 1,
          }}
          suppressTerraformOreConfirmation={suppressTerraformOreConfirmation}
          onSuppressTerraformOreConfirmation={() => setSuppressTerraformOreConfirmation(true)}
          onConfirm={(action) => {
            gameActions.sendAction(action);
            setRangePreviewQic(0);
          }}
          onClose={() => {
            if (planetPopup.buildAction) cancelCurrentAction();
            else { setRangePreviewQic(0); closeBoardContext(); }
          }}
        />
      )}
      {spaceshipPopup && (() => {
        const spaceshipBoard = gameState.spaceship_boards.find(({ id }) => id === spaceshipPopup.ship);
        if (!spaceshipBoard) return null;
        return (
          <SpaceshipExplorePopup
            anchor={spaceshipPopup.anchor}
            ship={spaceshipPopup.ship}
            spaceshipBoard={spaceshipBoard}
            board={gameState.board}
            player={me}
            selectedRangeQic={gameState.tutorial ? informationCubesNeededForRange(gameState.board, me, gameState.board.spaceship_tiles[spaceshipPopup.ship]!) ?? 0 : rangePreviewQic}
            onConfirm={() => {
              gameActions.sendAction({ type: 'ExploreSpaceship', ship: spaceshipPopup.ship });
              setRangePreviewQic(0);
            }}
            onClose={() => {
              setRangePreviewQic(0);
              closeBoardContext();
            }}
          />
        );
      })()}
      {!replay && undoPending === null && pendingDecisionPlayer === myId && (
        <section className="pending-decision-popup" role="dialog" aria-modal="false" aria-label="필수 게임 결정">
          <ActionPanel gameState={gameState} myPlayerId={myId} />
        </section>
      )}
      {selectedAction === 'FormFederation' && (
        <DraggableActionPopup className="federation-action-popup" label="연방 구축">
          <ActionPanel
            gameState={gameState}
            myPlayerId={myId}
            focusedAction
            federationTokenChoice={federationTokenChoice}
            onFederationTokenChoice={(choice) => {
              if (choice) handleFederationTokenChoice(choice);
              else setFederationTokenChoice(null);
            }}
            hideFederationTokenChoices
            federationBonusCoord={federationBonusCoord}
            onFederationBonusCoord={setFederationBonusCoord}
            federationBonusTechTile={federationBonusTechTile}
            federationBonusResearchTrack={federationBonusResearchTrack}
            hideFederationTechPicker
          />
        </DraggableActionPopup>
      )}
      </GameCommandControls>
      {!replay && tutorialOpen && (
        <FloatingBoardPanel title="도움말 · 따라 하기와 행동 설명" onClose={() => setTutorialOpen(false)}>
          {gameState.tutorial ? <Tutorial compact /> : <TutorialPanel events={gameState.event_log} myPlayerId={myPlayerId} />}
        </FloatingBoardPanel>
      )}
      {personalBoardPlayer && (
        <PersonalBoardDrawer
          title={`${personalBoardPlayer.nickname} · 개인 보드`}
          onClose={() => setPersonalBoardPlayerId(null)}
        >
          <PlayerDashboard player={personalBoardPlayer} />
        </PersonalBoardDrawer>
      )}
    </div>
    </LiveHighlightScope>
  );
}

function researchLevel(
  player: {
    research_tracks: {
      terraforming: number;
      navigation: number;
      ai: number;
      gaia: number;
      economy: number;
      science: number;
    };
  },
  track: ResearchTrack,
): number {
  switch (track) {
    case 'Terraforming':
      return player.research_tracks.terraforming;
    case 'Navigation':
      return player.research_tracks.navigation;
    case 'ArtificialIntelligence':
      return player.research_tracks.ai;
    case 'GaiaProject':
      return player.research_tracks.gaia;
    case 'Economy':
      return player.research_tracks.economy;
    case 'Science':
      return player.research_tracks.science;
  }
}
