import { useCallback, useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent, ReactNode } from 'react';
import { shallow } from 'zustand/shallow';
import { CalibrationView } from './components/CalibrationView';
import { ShuttlePreview } from './components/ShuttlePreview';
import { GameLobby } from './components/GameLobby';
import { FactionSelectView } from './components/GameLobby/FactionSelectView';
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
import { BoardOverlay } from './components/BoardOverlay';
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
} from './components/PlanetActionPopup';
import { selectableFederationHexes } from './components/federationSelection';
import { GameLog } from './components/GameLog';
import { SidebarTurnControls } from './components/SidebarTurnControls';
import { TopPassControl } from './components/TopPassControl';
import { GameOverScreen } from './components/GameOverScreen';
import { isSpaceshipBoardAction } from './components/boardActionSpaces';
import { useGameStore } from './store/gameStore';
import { useRoomStore } from './store/roomStore';
import { GaiaWebSocket } from './api/websocket';
import { api } from './api/rest';
import type { GameAction, Hex, HexCoord, ResearchTrack, ServerMessage, SpaceshipId, StructureType, TechTileChoice } from './types/game';
import { activeActionPlayerId, isGameState, pendingDecisionPlayerId } from './types/game';

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
}

interface BoardSpaceshipPopupState {
  ship: SpaceshipId;
  anchor: { x: number; y: number };
}

type TechUpgradeFlow =
  | {
      stage: 'tile';
      coord: HexCoord;
      to: StructureType;
      anchor: { x: number; y: number };
    }
  | {
      stage: 'track';
      coord: HexCoord;
      to: StructureType;
      anchor: { x: number; y: number };
      tile: number;
    }
  | {
      stage: 'bonus-mine';
      coord: HexCoord;
      to: StructureType;
      anchor: { x: number; y: number };
      tile: number;
      advanceTrack: ResearchTrack | null;
    }
  | {
      stage: 'cover';
      coord: HexCoord;
      to: StructureType;
      anchor: { x: number; y: number };
      tile: number;
      track: ResearchTrack;
    }
  | {
      stage: 'advanced-track';
      coord: HexCoord;
      to: StructureType;
      anchor: { x: number; y: number };
      track: ResearchTrack;
      coveredTile: number;
    };

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
      style={position ? { left: position.left, top: position.top, right: 'auto', bottom: 'auto' } : undefined}
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

export function App() {
  const [view, setView] = useState<AppView>('lobby');
  const [devGameLaunchError, setDevGameLaunchError] = useState<string | null>(null);
  const [devGameReady, setDevGameReady] = useState(false);
  const [activeBoardOverlay, setActiveBoardOverlay] = useState<'scoring' | 'boosters' | null>(null);
  const [personalBoardPlayerId, setPersonalBoardPlayerId] = useState<number | null>(null);
  const [structurePopup, setStructurePopup] = useState<BoardStructurePopupState | null>(null);
  const [planetPopup, setPlanetPopup] = useState<BoardPlanetPopupState | null>(null);
  const [spaceshipPopup, setSpaceshipPopup] = useState<BoardSpaceshipPopupState | null>(null);
  const [techUpgradeFlow, setTechUpgradeFlow] = useState<TechUpgradeFlow | null>(null);
  const [sidebarTab, setSidebarTab] = useState<'info' | 'log'>('info');
  const [rangePreviewQic, setRangePreviewQic] = useState(0);
  const [gameNotice, setGameNotice] = useState<string | null>(null);
  const [suppressTerraformOreConfirmation, setSuppressTerraformOreConfirmation] = useState(false);
  const [devPowerChargeTargeting, setDevPowerChargeTargeting] = useState(false);
  const [boardArtifactId, setBoardArtifactId] = useState<number | null>(null);
  const [shipActionOptions, setShipActionOptions] = useState<GameAction['type'][]>([]);
  const devGameLaunchStarted = useRef(false);
  const searchParams = new URLSearchParams(window.location.search);
  const devGameRequested = searchParams.get('devGame') === '1';

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
      actions: s.actions,
    }),
    shallow,
  );

  useEffect(() => {
    if (!devGameRequested || devGameLaunchStarted.current) return;
    devGameLaunchStarted.current = true;

    void api
      .createDevGame()
      .then((response) => {
        roomActions.setRoomInfo({
          roomCode: response.room_code,
          playerId: response.player_id,
          sessionToken: response.session_token,
          playerCount: response.players.length,
          roomState: 'faction_selection',
          gameSetup: response.game_setup,
          nickname: 'DEV',
          lobbyPlayers: response.players,
          hostPlayerId: response.host_player_id,
          revision: 0,
          paused: false,
          missingSeats: [],
          lastError: null,
        });
        gameActions.setMyPlayerId(response.player_id);
        gameActions.setGameState(response.game_state);
        setDevGameReady(true);
      })
      .catch((error: unknown) => {
        setDevGameLaunchError(error instanceof Error ? error.message : String(error));
      });
  }, [devGameRequested, gameActions, roomActions]);

  useEffect(() => {
    if (view !== 'game' || !roomCode || !sessionToken) return;

    const client = new GaiaWebSocket(roomCode);
    gameActions.setWsClient(client);

    client.on((msg: ServerMessage) => {
      switch (msg.type) {
        case 'snapshot':
          roomActions.setRevision(msg.revision);
          if (isGameState(msg.state)) {
            gameActions.setGameState(msg.state);
          }
          break;
        case 'command_accepted':
          roomActions.setRevision(msg.revision);
          roomActions.setError(null);
          break;
        case 'command_rejected':
          roomActions.setRevision(msg.revision);
          roomActions.setError({
            code: msg.rejection.code,
            message: msg.rejection.message_key,
          });
          break;
        case 'room_joined':
          gameActions.setMyPlayerId(msg.player_id);
          roomActions.setRevision(msg.revision);
          break;
        case 'game_ended':
          gameActions.setFinalResult({
            finalScores: msg.final_scores,
            winner: msg.winner,
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
      client.disconnect();
      gameActions.setWsClient(null);
    };
  }, [view, roomCode, sessionToken]);

  useEffect(() => {
    if (playerId !== null) {
      gameActions.setMyPlayerId(playerId);
    }
  }, [playerId]);

  const handleGameStart = useCallback(() => {
    setView('game');
  }, []);

  // Debug-only coordinate picker for measuring image-relative slot
  // positions (see `CalibrationView`) — never linked to from in-game UI,
  // reached only by appending this query param by hand.
  if (searchParams.get('shuttlePreview') === '1') {
    return <ShuttlePreview />;
  }
  if (searchParams.get('calibrate') === '1') {
    return <CalibrationView />;
  }

  if (devGameRequested && view === 'lobby' && !devGameReady) {
    return (
      <div className="app app--loading">
        {devGameLaunchError ? (
          <p>개발 게임 생성 실패: {devGameLaunchError}</p>
        ) : (
          <>
            <div className="spinner" />
            <p>실제 엔진 샌드박스를 여는 중...</p>
          </>
        )}
      </div>
    );
  }

  if (devGameRequested && view === 'lobby') {
    return (
      <div className="app app--lobby">
        <FactionSelectView onGameStart={handleGameStart} emphasizeStructures />
      </div>
    );
  }

  function handleReturnToLobby() {
    gameActions.reset();
    roomActions.reset();
    setView('lobby');
  }

  if (view === 'game' && finalResult && gameState) {
    return (
      <GameOverScreen
        result={finalResult}
        players={gameState.players}
        myPlayerId={myPlayerId ?? 0}
        onReturnToLobby={handleReturnToLobby}
      />
    );
  }

  if (view === 'lobby') {
    return (
      <div className="app app--lobby">
        <GameLobby onGameStart={handleGameStart} />
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
  const personalBoardPlayer =
    personalBoardPlayerId === null
      ? null
      : (gameState.players.find((player) => player.player_id === personalBoardPlayerId) ?? null);
  const activePlayerId = activeActionPlayerId(gameState);
  const undoPending = gameState.undo_state?.pending_request ?? null;
  const isMyActionTurn = activePlayerId === myId && undoPending === null;
  const hasServerFreeActions = gameState.undo_state?.open_turn?.player === myId
    && (gameState.undo_state.open_turn.free_action_revisions.length ?? 0) > 0;
  const usedPowerActions = gameState.used_power_actions;
  const lostPlanetPending =
    typeof gameState.phase === 'object' && 'LostPlanetPlacementPending' in gameState.phase
      ? gameState.phase.LostPlanetPlacementPending
      : null;
  const isMyLostPlanetPlacement = lostPlanetPending?.player === myId;
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

  function handleResearchBoardAction(id: number) {
    if (!isMyActionTurn || usedPowerActions.includes(id)) return;
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
  }

  function handleOwnedStructureClick(hex: Hex, anchor: { x: number; y: number }) {
    const structure = hex.structures.find(({ owner }) => owner === myId);
    if (!structure || !isMyActionTurn) return;
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
    if ((!devGameRequested && powerActionId === undefined)
      || !hex.planet
      || hex.structures.length > 0
      || !isMyActionTurn) return;
    const occupiedByOther = hex.planet.owner !== null && !(hex.planet.owner === myId && hex.planet.is_gaia_formed);
    if (occupiedByOther) return;
    const rangeNotice = rangeRequirementNotice(
      informationCubesNeededForRange(gameState!.board, me, hex.coord),
      rangePreviewQic,
    );
    if (rangeNotice) {
      setGameNotice(rangeNotice);
      closeBoardContext();
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
    if (!isMyActionTurn) return;
    gameActions.selectAction(null);
    setGameNotice(null);
    setStructurePopup(null);
    setPlanetPopup(null);
    setTechUpgradeFlow(null);
    setSpaceshipPopup({ ship, anchor });
  }

  function handleArtifactClick(artifactId: number) {
    if (!isMyActionTurn) return;
    closeBoardContext();
    setShipActionOptions([]);
    setBoardArtifactId(artifactId);
    gameActions.selectAction('ExamineArtifact');
  }

  function handleShipActionSelect(
    actionType: GameAction['type'],
    actionTypes: GameAction['type'][],
  ) {
    if (!isMyActionTurn) return;
    closeBoardContext();
    setBoardArtifactId(null);
    setShipActionOptions(actionTypes);
    gameActions.selectAction(actionType);
  }

  function handleUpgradeChoice(to: StructureType) {
    if (!structurePopup || !gameState) return;
    if (!canPayForUpgrade(me, gameState.board, structurePopup.coord, structurePopup.structure, to)) {
      return;
    }
    const grantsTechTile = to === 'ResearchLab' || typeof to === 'object';
    if (grantsTechTile) {
      if (selectableStandardTiles.length === 0 && selectableAdvancedTracks.length === 0) {
        gameActions.sendAction({
          type: 'Upgrade',
          coord: structurePopup.coord,
          to,
          tech_tile_choice: null,
        });
        closeBoardContext();
        return;
      }
      setTechUpgradeFlow({
        stage: 'tile',
        coord: structurePopup.coord,
        to,
        anchor: structurePopup.anchor,
      });
      setStructurePopup(null);
      return;
    }
    gameActions.sendAction({
      type: 'Upgrade',
      coord: structurePopup.coord,
      to,
      tech_tile_choice: null,
    });
    closeBoardContext();
  }

  function startFederationFromStructure() {
    if (!structurePopup) return;
    const coord = structurePopup.coord;
    closeBoardContext();
    gameActions.selectAction('FormFederation');
    gameActions.toggleHex(coord);
  }

  function sendTechUpgrade(choice: TechTileChoice) {
    if (!techUpgradeFlow) return;
    gameActions.sendAction({
      type: 'Upgrade',
      coord: techUpgradeFlow.coord,
      to: techUpgradeFlow.to,
      tech_tile_choice: choice,
    });
    closeBoardContext();
  }

  function finishStandardTechChoice(tile: number, advanceTrack: ResearchTrack | null) {
    if (!techUpgradeFlow) return;
    if (tile === 11) {
      setTechUpgradeFlow({
        stage: 'bonus-mine',
        coord: techUpgradeFlow.coord,
        to: techUpgradeFlow.to,
        anchor: techUpgradeFlow.anchor,
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
    if (techUpgradeFlow?.stage === 'track') {
      finishStandardTechChoice(techUpgradeFlow.tile, track);
    } else if (techUpgradeFlow?.stage === 'advanced-track') {
      sendTechUpgrade({
        kind: 'Advanced',
        track: techUpgradeFlow.track,
        covered_tile: techUpgradeFlow.coveredTile,
        advance_track: track,
      });
    }
  }

  function handlePaidResearchTrack(track: ResearchTrack) {
    if (!isMyActionTurn || me.resources.knowledge < 4) return;
    closeBoardContext();
    gameActions.sendAction({ type: 'ResearchAdvance', track });
  }

  function handleAdvancedTechTile(tile: number, track: ResearchTrack) {
    if (techUpgradeFlow?.stage !== 'tile') return;
    setTechUpgradeFlow({ ...techUpgradeFlow, stage: 'cover', tile, track });
  }

  function handleCoveredTechTile(tile: number) {
    if (techUpgradeFlow?.stage !== 'cover') return;
    if (selectableTechResearchTracks.length === 0) {
      sendTechUpgrade({
        kind: 'Advanced',
        track: techUpgradeFlow.track,
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
        kind: 'Advanced',
        track: techUpgradeFlow.track,
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

  const ownedUncoveredTechTiles = (me.tech_tiles ?? []).filter((tile) => !(me.covered_tech_tiles ?? []).includes(tile));
  const selectableResearchBoardTechTiles = (gameState.research_board.tech_tile_slots ?? []).filter(
    (tile): tile is number => tile !== null && !(me.tech_tiles ?? []).includes(tile),
  );
  const selectableSpaceshipTechTiles = gameState.spaceship_boards
    .filter((board) => board.explorers.includes(myId))
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
  const selectableTechResearchTracks = RESEARCH_TRACK_ORDER.filter((track) => {
    const level = researchLevel(me, track);
    if (level >= 5) return false;
    if (me.faction === 'BalTaks'
      && track === 'Navigation'
      && !me.structures.some(({ kind }) => kind === 'PlanetaryInstitute')) return false;
    if (level < 4) return true;
    return greenFederationTokenCount > 0
      && !gameState.players.some((player) => player.player_id !== myId && researchLevel(player, track) >= 5);
  });
  const bonusMineTargets =
    techUpgradeFlow?.stage === 'bonus-mine' ? Object.values(gameState.board.hexes).map((hex) => hex.coord) : [];
  const federationSelectableHexes = selectedAction === 'FormFederation'
    ? selectableFederationHexes(gameState, myId, selectedHexes)
    : [];
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
    <div className="app app--game">
      {(lastError || gameNotice) && (
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
      <nav className="game-topbar" aria-label="게임 정보">
        {devGameRequested && (
          <button className="game-top-control" onClick={() => window.location.reload()}>
            DEV · 새 게임
          </button>
        )}
        <button
          className="game-top-control"
          onClick={() => setActiveBoardOverlay((current) => (current === 'scoring' ? null : 'scoring'))}
        >
          라운드·게임 종료 목표
        </button>
        <button
          className="game-top-control"
          onClick={() => setActiveBoardOverlay((current) => (current === 'boosters' ? null : 'boosters'))}
        >
          라운드 부스터
        </button>
        <button className="game-top-control" onClick={() => setPersonalBoardPlayerId(myId)}>
          개인 보드
        </button>
        <TopPassControl
          player={me}
          round={gameState.round}
          availableBoosters={gameState.boosters}
          isMyTurn={isMyActionTurn}
          onPass={(boosterId) => gameActions.sendAction({ type: 'Pass', booster_id: boosterId })}
        />
      </nav>
      <aside className="game-reference-rail" aria-label="공용 트랙과 함선 보드">
        <section className="game-reference-card">
          <h2>연구 트랙</h2>
          <ResearchBoard
            players={gameState.players}
            board={gameState.research_board}
            usedPowerActions={gameState.used_power_actions}
            isMyTurn={isMyActionTurn}
            selectedPowerActionId={selectedPowerActionId}
            onPowerAction={handleResearchBoardAction}
            techSelectionMode={
              techUpgradeFlow?.stage === 'tile' ? 'tile' : techUpgradeFlow?.stage === 'track' ? 'track' : null
            }
            selectableStandardTiles={selectableStandardTiles}
            selectableAdvancedTracks={selectableAdvancedTracks}
            selectableResearchTracks={selectableTechResearchTracks}
            onStandardTechTile={handleStandardTechTile}
            onAdvancedTechTile={handleAdvancedTechTile}
            onResearchTrack={handleTechResearchTrack}
            onPaidResearchTrack={
              techUpgradeFlow === null && isMyActionTurn ? handlePaidResearchTrack : undefined
            }
          />
        </section>
        <section className="game-ship-list" aria-label="함선 보드 영역">
          <h2>함선 보드</h2>
          <SpaceshipBoards
            spaceshipBoards={gameState.spaceship_boards}
            players={gameState.players}
            myPlayerId={myId}
            isMyTurn={isMyActionTurn}
            usedActionIds={gameState.used_spaceship_actions}
            selectedAction={selectedAction}
            selectableTechTiles={techUpgradeFlow?.stage === 'tile' ? selectableStandardTiles : []}
            onActionSelect={handleShipActionSelect}
            onArtifactSelect={handleArtifactClick}
            onTechTileSelect={
              techUpgradeFlow?.stage === 'tile'
                ? (tile) => handleStandardTechTile(tile, -1)
                : undefined
            }
          />
        </section>
      </aside>
      <main className="game-board-stage">
        <GameBoard
          board={gameState.board}
          players={gameState.players}
          validTargets={isMyLostPlanetPlacement ? lostPlanetTargets : bonusMineTargets}
          federationSelectableHexes={federationSelectableHexes}
          selectedCoord={isMyLostPlanetPlacement ? activePlanet : null}
          onHexClick={
            isMyLostPlanetPlacement
              ? gameActions.selectPlanet
              : techUpgradeFlow?.stage === 'bonus-mine'
                ? handleBonusMineTarget
                : undefined
          }
          interactivePlayerId={isMyActionTurn ? myId : undefined}
          onOwnedStructureClick={isMyActionTurn ? handleOwnedStructureClick : undefined}
          onPlanetClick={
            isMyActionTurn && (devGameRequested || selectedTerraformingPowerAction)
              ? handlePlanetClick
              : undefined
          }
          onSpaceshipClick={isMyActionTurn ? handleSpaceshipClick : undefined}
          allowPlanetPopupDuringSelectedAction={selectedTerraformingPowerAction}
          devPowerChargeTargeting={devPowerChargeTargeting}
          onPowerChargeStructureClick={(hex) => {
            gameActions.triggerDevPowerCharge(hex.coord);
            setDevPowerChargeTargeting(false);
            closeBoardContext();
          }}
          onContextDismiss={closeBoardContext}
          emphasizeStructures={devGameRequested}
          rangePlayerId={devGameRequested ? myId : undefined}
          rangePreviewBonus={rangePreviewQic * 2}
        />
        <LostFleetTechRequirementBoard
          side={gameState.research_board.lost_fleet_advanced_tech_requirement}
          tileId={gameState.research_board.lost_fleet_advanced_tech_tile}
        />
      </main>
      <aside className="game-sidebar">
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
          </button>
        </div>
        {sidebarTab === 'info' ? (
          <div
            className="game-sidebar-tab-panel game-sidebar-tab-panel--info"
            id="game-sidebar-info-panel"
            role="tabpanel"
            aria-labelledby="game-sidebar-info-tab"
          >
            <OpponentPanels
              players={orderedPlayers}
              myPlayerId={myId}
              activePlayerId={activePlayerId}
              events={gameState.event_log ?? []}
              round={gameState.round}
              economyResearchTileSide={gameState.research_board.economy_research_tile_side}
              onPlayerSelect={(player) => setPersonalBoardPlayerId(player.player_id)}
            />
            <SidebarTurnControls
              player={me}
              isMyTurn={isMyActionTurn}
              onFreeAction={(kind) => gameActions.sendAction({ type: 'FreeAction', kind, count: 1 })}
              rangePreviewQic={rangePreviewQic}
              onRangePreviewAdd={() => {
                setGameNotice(null);
                setRangePreviewQic((current) => Math.min(current + 1, me.resources.qic));
              }}
              showDevPowerChargeTest={devGameRequested}
              devPowerChargeTargeting={devPowerChargeTargeting}
              onDevPowerChargeToggle={() => {
                closeBoardContext();
                setDevPowerChargeTargeting((active) => !active);
              }}
              undoState={gameState.undo_state}
              players={gameState.players}
              onUndoFreeAction={() => {
                setRangePreviewQic(0);
                setGameNotice(null);
                if (hasServerFreeActions) gameActions.undoFreeAction();
              }}
              onRequestTurnUndo={gameActions.requestTurnUndo}
              onRespondTurnUndo={gameActions.respondTurnUndo}
            />
          </div>
        ) : (
          <div
            className="game-sidebar-tab-panel game-sidebar-tab-panel--log"
            id="game-sidebar-log-panel"
            role="tabpanel"
            aria-labelledby="game-sidebar-log-tab"
          >
            <GameLog events={gameState.event_log ?? []} players={gameState.players} />
          </div>
        )}
      </aside>
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
            closeBoardContext();
          }}
          onClose={() => {
            setRangePreviewQic(0);
            closeBoardContext();
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
            selectedRangeQic={rangePreviewQic}
            onConfirm={() => {
              gameActions.sendAction({ type: 'ExploreSpaceship', ship: spaceshipPopup.ship });
              setRangePreviewQic(0);
              closeBoardContext();
            }}
            onClose={() => {
              setRangePreviewQic(0);
              closeBoardContext();
            }}
          />
        );
      })()}
      {undoPending === null && pendingDecisionPlayer === myId && (
        <section className="pending-decision-popup" role="dialog" aria-modal="false" aria-label="필수 게임 결정">
          <ActionPanel gameState={gameState} myPlayerId={myId} />
        </section>
      )}
      {selectedAction === 'FormFederation' && (
        <DraggableActionPopup className="federation-action-popup" label="연방 구축">
          <ActionPanel gameState={gameState} myPlayerId={myId} focusedAction />
        </DraggableActionPopup>
      )}
      {(isSpaceshipBoardAction(selectedAction) || selectedAction === 'ExamineArtifact') && (
        <DraggableActionPopup className="ship-action-popup" label="함선 행동">
          <ActionPanel
            gameState={gameState}
            myPlayerId={myId}
            focusedAction
            focusedActionOptions={shipActionOptions}
            initialArtifactId={boardArtifactId}
          />
        </DraggableActionPopup>
      )}
      {activeBoardOverlay === 'scoring' && (
        <BoardOverlay title="라운드·게임 종료 목표" onClose={() => setActiveBoardOverlay(null)}>
          <ScoringBoard
            roundTiles={gameState.round_tiles}
            finalScoringTiles={gameState.final_scoring_tiles}
            currentRound={gameState.round}
          />
        </BoardOverlay>
      )}
      {activeBoardOverlay === 'boosters' && (
        <BoardOverlay title="라운드 부스터 · 연방 토큰" onClose={() => setActiveBoardOverlay(null)}>
          <RoundBoosters availableBoosters={gameState.boosters} players={gameState.players} />
          <FederationTokens availableTokens={gameState.research_board.federation_tokens} players={gameState.players} />
        </BoardOverlay>
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
