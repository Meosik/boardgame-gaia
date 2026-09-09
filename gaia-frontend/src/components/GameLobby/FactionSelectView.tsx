import { useEffect, useMemo, useRef, useState } from 'react';
import { shallow } from 'zustand/shallow';
import { useRoomStore } from '../../store/roomStore';
import { useGameStore } from '../../store/gameStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { GameBoard } from '../GameBoard';
import { PlayerDashboard } from '../PlayerDashboard';
import { ResearchBoard } from '../PlayerDashboard/ResearchBoard';
import { OpponentPanels } from '../OpponentPanels';
import { SpaceshipBoards } from '../SpaceshipBoards';
import { LostFleetTechRequirementBoard } from '../LostFleetTechRequirementBoard';
import { FactionBadge } from './FactionBadge';
import { TerraformingSelectionBoard } from './TerraformingSelectionBoard';
import { explorationBoardImageSrc } from '../../assets/explorationBoardImages';
import { roundBoosterImageSrc } from '../../assets/roundBoosterImages';
import type {
  BidAssignment,
  BiddingStage,
  BiddingState,
  FactionAssignment,
  FactionId,
  FactionSelectionState,
  GameState,
  HexCoord,
  PlanetType,
  PlayerId,
  SetupAction,
  SetupPhase,
  StructureType,
} from '../../types/game';
import { isGameState } from '../../types/game';

interface Props {
  onGameStart: () => void;
  emphasizeStructures?: boolean;
}

function initialSelectionState(
  playerOrder: PlayerId[],
  factions: FactionId[],
): FactionSelectionState {
  return {
    available_factions: factions,
    player_order: playerOrder,
    current_index: 0,
    assignments: [],
  };
}

function initialBiddingState(
  playerOrder: PlayerId[],
  factions: FactionId[],
): BiddingState | null {
  const firstPlayer = playerOrder[0];
  if (firstPlayer === undefined || playerOrder.length !== 4 || factions.length !== 4) {
    return null;
  }
  return {
    clockwise_order: playerOrder,
    remaining_players: playerOrder,
    available_factions: factions,
    available_turn_positions: [1, 2, 3, 4],
    active_player: firstPlayer,
    highest_bid: 0,
    highest_bidder: null,
    passed_players: [],
    stage: 'Auction',
    assignments: [],
  };
}

function biddingActor(stage: BiddingStage, activePlayer: PlayerId): PlayerId | null {
  if (stage === 'Auction') return activePlayer;
  if (stage === 'Complete') return null;
  return stage.WinnerChoice.winner;
}

type StartingStructurePhase = Extract<SetupPhase, { StartingStructures: unknown }>['StartingStructures'];
type StartingBoosterPhase = Extract<SetupPhase, { StartingBoosters: unknown }>['StartingBoosters'];

/// Not a rulebook limit — mirrors `gaia_engine::bidding::MAX_BID`, a flat
/// sanity ceiling only (a bid may legitimately exceed the bidder's current
/// 승점 and just run their final score negative). Matching it here just lets
/// the UI reject an obvious garbage input before it round-trips to the
/// server.
const MAX_BID = 100;

const HOME_PLANET_BY_FACTION: Record<FactionId, PlanetType> = {
  Terrans: 'Terra',
  Lantids: 'Terra',
  Xenos: 'Desert',
  Gleens: 'Desert',
  Taklons: 'Swamp',
  Ambas: 'Swamp',
  HadschHallas: 'Oxide',
  Ivits: 'Oxide',
  Geodens: 'Volcanic',
  BalTaks: 'Volcanic',
  Firaks: 'Titanium',
  Bescods: 'Titanium',
  Nevlas: 'Ice',
  Itars: 'Ice',
  Tinkeroids: 'Asteroid',
  Darkanians: 'Asteroid',
  Moweyds: 'ProtoPlanet',
  SpaceGiants: 'ProtoPlanet',
};

function startingStructurePhase(state: GameState | null): StartingStructurePhase | null {
  if (!state || typeof state.phase !== 'object' || !('Setup' in state.phase)) return null;
  const setup = state.phase.Setup;
  if (typeof setup !== 'object' || !('StartingStructures' in setup)) return null;
  return setup.StartingStructures;
}

function startingBoosterPhase(state: GameState | null): StartingBoosterPhase | null {
  if (!state || typeof state.phase !== 'object' || !('Setup' in state.phase)) return null;
  const setup = state.phase.Setup;
  if (typeof setup !== 'object' || !('StartingBoosters' in setup)) return null;
  return setup.StartingBoosters;
}

function structureLabel(kind: StructureType): string {
  if (kind === 'Mine') return '광산';
  if (kind === 'PlanetaryInstitute') return '행성 의회';
  if (kind === 'TradingStation') return '교역소';
  if (kind === 'ResearchLab') return '연구소';
  if (kind === 'Satellite') return '위성';
  if (kind === 'SpaceStation') return '우주 정거장';
  return '아카데미';
}

export function FactionSelectView({ onGameStart, emphasizeStructures = false }: Props) {
  const {
    roomCode,
    sessionToken,
    nickname,
    gameSetup,
    playerId,
    lobbyPlayers,
    revision,
    setRevision,
  } = useRoomStore(
    (state) => ({
      roomCode: state.roomCode!,
      sessionToken: state.sessionToken,
      nickname: state.nickname,
      gameSetup: state.gameSetup,
      playerId: state.playerId,
      lobbyPlayers: state.lobbyPlayers,
      revision: state.revision,
      setRevision: state.actions.setRevision,
    }),
    shallow,
  );
  const initialGameState = useGameStore((state) => state.gameState);
  const setGameState = useGameStore((state) => state.actions.setGameState);
  const { isConnected, send, sendCommand, messages } = useWebSocket(roomCode);
  const [setupGameState, setSetupGameState] = useState<GameState | null>(initialGameState);
  const [bidAmount, setBidAmount] = useState(1);
  const [selectedFaction, setSelectedFaction] = useState<FactionId | null>(null);
  const [selectedTurnPosition, setSelectedTurnPosition] = useState<number | null>(null);
  const [selectedStartingHex, setSelectedStartingHex] = useState<HexCoord | null>(null);
  const [selectedStartingBooster, setSelectedStartingBooster] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const playerNames = useMemo(
    () => new Map(lobbyPlayers.map((player) => [player.player_id, player.nickname])),
    [lobbyPlayers],
  );
  const playerOrder = useMemo(
    () => lobbyPlayers.map((player) => player.player_id),
    [lobbyPlayers],
  );
  const initialSelection = useMemo(
    () => initialSelectionState(playerOrder, gameSetup?.factions ?? []),
    [gameSetup?.factions, playerOrder],
  );
  const initialBidding = useMemo(
    () => initialBiddingState(playerOrder, gameSetup?.factions ?? []),
    [gameSetup?.factions, playerOrder],
  );
  const isBiddingMode = gameSetup?.setup_mode === 'bidding' || setupGameState?.bidding != null;
  const selection = setupGameState?.faction_selection ?? initialSelection;
  const bidding = setupGameState?.bidding ?? initialBidding;
  const startingPlacement = startingStructurePhase(setupGameState);
  const startingBooster = startingBoosterPhase(setupGameState);
  const startingPlayer = startingPlacement
    ? setupGameState?.players.find(
        (player) => player.player_id === startingPlacement.active_player,
      ) ?? null
    : null;
  const startingFaction = startingPlayer?.faction ?? null;
  const validStartingTargets = useMemo(() => {
    if (!setupGameState || !startingFaction) return [];
    const homePlanet = HOME_PLANET_BY_FACTION[startingFaction];
    return Object.values(setupGameState.board.hexes)
      .filter((hex) =>
        hex.planet?.planet_type === homePlanet &&
        !hex.planet.is_gaia_formed &&
        hex.planet.owner === null &&
        hex.structures.length === 0,
      )
      .map((hex) => hex.coord);
  }, [setupGameState, startingFaction]);

  useEffect(() => {
    if (isConnected && sessionToken) {
      send({
        type: 'join_room',
        room_code: roomCode,
        nickname,
        session_token: sessionToken,
      });
    }
  }, [isConnected, nickname, roomCode, send, sessionToken]);

  // Processes every message received since the last run, in order — see
  // `useWebSocket`'s `messages` doc comment. This matters throughout the
  // whole setup flow here, not just the initial transition: `snapshot`
  // drives every step (bidding progress, starting-structure/booster turns),
  // and losing one to a same-batch sibling would stall whichever step it
  // was carrying.
  const processedCount = useRef(0);
  useEffect(() => {
    for (let i = processedCount.current; i < messages.length; i++) {
      const message = messages[i];
      switch (message.type) {
        case 'room_joined':
        case 'command_accepted':
          setRevision(message.revision);
          setErrorMessage(null);
          break;
        case 'command_rejected':
          setRevision(message.revision);
          setErrorMessage(message.rejection.message_key);
          break;
        case 'error':
          setErrorMessage(message.message);
          break;
        case 'snapshot': {
          setRevision(message.revision);
          const { state } = message;
          if (!isGameState(state)) break;
          if (typeof state.phase === 'object' && 'Setup' in state.phase) {
            setSetupGameState(state);
            break;
          }
          setGameState(state);
          onGameStart();
          break;
        }
      }
    }
    processedCount.current = messages.length;
  }, [messages, onGameStart, setGameState, setRevision]);

  useEffect(() => {
    if (!bidding) return;
    setBidAmount(bidding.highest_bid + 1);
  }, [bidding?.highest_bid]);

  useEffect(() => {
    setSelectedFaction(null);
    setSelectedTurnPosition(null);
  }, [bidding?.stage]);

  useEffect(() => {
    setSelectedStartingHex(null);
  }, [startingPlacement?.placement_index]);

  useEffect(() => {
    setSelectedStartingBooster(null);
  }, [startingBooster?.selection_index]);

  function playerLabel(id: PlayerId) {
    return playerNames.get(id)
      ?? setupGameState?.players.find((player) => player.player_id === id)?.nickname
      ?? `P${id}`;
  }

  function sendSetupAction(action: SetupAction) {
    setErrorMessage(null);
    sendCommand({ type: 'place_setup_action', action }, revision);
  }

  if (startingPlacement && setupGameState && startingPlayer && startingFaction) {
    const isMyTurn = playerId !== null && startingPlacement.active_player === playerId;
    return (
      <StartingStructureSetup
        game={setupGameState}
        placement={startingPlacement}
        activeFaction={startingFaction}
        isMyTurn={isMyTurn}
        isConnected={isConnected}
        selectedHex={selectedStartingHex}
        validTargets={validStartingTargets}
        errorMessage={errorMessage}
        playerLabel={playerLabel}
        emphasizeStructures={emphasizeStructures}
        onSelectHex={(coord) => {
          if (isMyTurn) setSelectedStartingHex(coord);
        }}
        onConfirm={() => {
          if (!isMyTurn || selectedStartingHex === null) return;
          sendSetupAction({ type: 'PlaceStartingStructure', coord: selectedStartingHex });
        }}
      />
    );
  }

  if (startingBooster && setupGameState) {
    const isMyTurn = playerId !== null && startingBooster.active_player === playerId;
    return (
      <StartingBoosterSetup
        game={setupGameState}
        selection={startingBooster}
        isMyTurn={isMyTurn}
        isConnected={isConnected}
        selectedBooster={selectedStartingBooster}
        errorMessage={errorMessage}
        playerLabel={playerLabel}
        emphasizeStructures={emphasizeStructures}
        onSelectBooster={(boosterId) => {
          if (isMyTurn) setSelectedStartingBooster(boosterId);
        }}
        onConfirm={() => {
          if (!isMyTurn || selectedStartingBooster === null) return;
          sendSetupAction({
            type: 'SelectStartingBooster',
            booster_id: selectedStartingBooster,
          });
        }}
      />
    );
  }

  if (isBiddingMode && bidding) {
    const actor = biddingActor(bidding.stage, bidding.active_player);
    const isMyTurn = playerId !== null && actor === playerId;
    const myVp = setupGameState?.players.find((player) => player.player_id === playerId)?.vp ?? 10;
    // The auction is decided by looking at the fully-set-up board (sector
    // layout, spaceship tiles, home planets, round/final scoring tiles) —
    // not just the faction list — so the whole board renders as the actual
    // page underneath, exactly like the normal in-game view, with the
    // bidding controls as a popup on top rather than replacing the board.
    return (
      <div className="app app--game bidding-preview">
        {setupGameState ? (
          <>
            <div className="game-main">
              <PlayerDashboard
                player={setupGameState.players.find((p) => p.player_id === playerId) ?? setupGameState.players[0]}
              />
              <GameBoard
                board={setupGameState.board}
                players={setupGameState.players}
                emphasizeStructures={emphasizeStructures}
              />
            </div>
            <div className="game-sidebar">
              <OpponentPanels
                players={setupGameState.players.filter((p) => p.player_id !== playerId)}
              />
            </div>
          </>
        ) : (
          <div className="app--loading">
            <div className="spinner" />
            <p>보드를 불러오는 중...</p>
          </div>
        )}
        <div className="bidding-modal-overlay">
          <div className="bidding-modal">
            <BiddingSetup
              bidding={bidding}
              actor={actor}
              isMyTurn={isMyTurn}
              myVp={myVp}
              bidAmount={bidAmount}
              selectedFaction={selectedFaction}
              selectedTurnPosition={selectedTurnPosition}
              isConnected={isConnected}
              errorMessage={errorMessage}
              playerLabel={playerLabel}
              terraformingColorOrder={
                setupGameState?.terraforming_color_order
                  ?? gameSetup?.terraforming_color_order
                  ?? []
              }
              onBidAmountChange={setBidAmount}
              onSelectFaction={setSelectedFaction}
              onSelectTurnPosition={setSelectedTurnPosition}
              onPlaceBid={() => sendSetupAction({ type: 'PlaceBid', amount: bidAmount })}
              onPass={() => sendSetupAction({ type: 'PassBid' })}
              onConfirmChoice={() => {
                if (selectedFaction === null || selectedTurnPosition === null) return;
                sendSetupAction({
                  type: 'ChooseBidReward',
                  faction: selectedFaction,
                  turn_position: selectedTurnPosition,
                });
              }}
            />
          </div>
        </div>
      </div>
    );
  }

  const activePlayer = selection.player_order[selection.current_index] ?? null;
  const isMyTurn = playerId !== null && activePlayer === playerId;
  const assignmentFor = (player: PlayerId): FactionAssignment | undefined =>
    selection.assignments.find((assignment) => assignment.player === player);

  return (
    <div className="faction-selection-view">
      <SetupHeader
        kicker="공식 시계방향 배치"
        title="종족 선택"
        isConnected={isConnected}
      />

      <TerraformingSelectionBoard
        colorOrder={
          setupGameState?.terraforming_color_order
            ?? gameSetup?.terraforming_color_order
            ?? []
        }
      />

      <section className="faction-selection-order" aria-label="종족 선택 순서">
        {selection.player_order.map((id, index) => {
          const assignment = assignmentFor(id);
          const isActive = index === selection.current_index;
          return (
            <div
              key={id}
              className={`faction-selection-player ${isActive ? 'active' : ''} ${assignment ? 'complete' : ''}`}
            >
              <span className="faction-selection-position">{index + 1}</span>
              <strong>{playerLabel(id)}</strong>
              <span>
                {assignment ? (
                  <FactionBadge
                    faction={assignment.faction}
                    size={28}
                    imageSrc={explorationBoardImageSrc(assignment.faction) ?? undefined}
                  />
                ) : isActive ? (
                  '선택 중'
                ) : (
                  '대기'
                )}
              </span>
            </div>
          );
        })}
      </section>

      <section className="faction-selection-panel">
        <div className="faction-selection-prompt">
          {isMyTurn
            ? '사용할 종족 보드 면을 선택하세요.'
            : `${activePlayer === null ? '선택 완료' : playerLabel(activePlayer)}님의 선택을 기다리는 중입니다.`}
        </div>
        <div className="faction-selection-grid">
          {selection.available_factions.map((faction) => (
            <FactionChoice
              key={faction}
              faction={faction}
              disabled={!isMyTurn}
              onClick={() => sendSetupAction({ type: 'SelectFaction', faction })}
            />
          ))}
        </div>
        {errorMessage && <p className="error-msg">{errorMessage}</p>}
      </section>
    </div>
  );
}

interface StartingStructureSetupProps {
  game: GameState;
  placement: StartingStructurePhase;
  activeFaction: FactionId;
  isMyTurn: boolean;
  isConnected: boolean;
  selectedHex: HexCoord | null;
  validTargets: HexCoord[];
  errorMessage: string | null;
  playerLabel: (id: PlayerId) => string;
  emphasizeStructures: boolean;
  onSelectHex: (coord: HexCoord) => void;
  onConfirm: () => void;
}

function StartingStructureSetup({
  game,
  placement,
  activeFaction,
  isMyTurn,
  isConnected,
  selectedHex,
  validTargets,
  errorMessage,
  playerLabel,
  emphasizeStructures,
  onSelectHex,
  onConfirm,
}: StartingStructureSetupProps) {
  const structure = structureLabel(placement.kind);
  const homePlanet = HOME_PLANET_BY_FACTION[activeFaction];
  const activePlayer = game.players.find((player) => player.player_id === placement.active_player);
  const factionPlacementNumber =
    (activePlayer?.structures.filter((candidate) => candidate.kind === placement.kind).length ?? 0) + 1;
  return (
    <div className="app app--game setup-game-preview starting-structure-layout">
      <nav className="game-topbar" aria-label="초기 설정 상태">
        <span className="game-top-control setup-phase-indicator">
          테란 초기 설정 · {factionPlacementNumber}번째 {structure} · 전체 {placement.placement_index + 1}단계
        </span>
      </nav>
      <aside className="game-reference-rail" aria-label="게임 참조 보드">
        <section className="game-reference-card">
          <h2>연구 트랙</h2>
          <ResearchBoard players={game.players} board={game.research_board} />
        </section>
        <section className="game-ship-list" aria-label="함선 보드 영역">
          <h2>함선 보드</h2>
          <SpaceshipBoards spaceshipBoards={game.spaceship_boards} players={game.players} />
        </section>
      </aside>
      <main className="game-board-stage">
        <GameBoard
          board={game.board}
          players={game.players}
          validTargets={validTargets}
          selectedCoord={selectedHex}
          onHexClick={onSelectHex}
          emphasizeStructures={emphasizeStructures}
        />
        <LostFleetTechRequirementBoard
          side={game.research_board.lost_fleet_advanced_tech_requirement}
          tileId={game.research_board.lost_fleet_advanced_tech_tile}
        />
      </main>
      <aside className="game-sidebar starting-structure-sidebar">
        <div className="faction-selection-view starting-structure-view">
          <SetupHeader kicker="INITIAL PLACEMENT" title="시작 구조물 배치" isConnected={isConnected} />

          <section className="faction-selection-order" aria-label="시작 구조물 배치 현황">
            {game.turn_order.map((id, index) => {
              const player = game.players.find((candidate) => candidate.player_id === id);
              const isActive = id === placement.active_player;
              return (
                <div key={id} className={`faction-selection-player ${isActive ? 'active' : ''}`}>
                  <span className="faction-selection-position">{index + 1}</span>
                  <strong>{playerLabel(id)}</strong>
                  <span className="starting-player-status">
                    {player?.faction && (
                      <FactionBadge
                        faction={player.faction}
                        size={26}
                        imageSrc={explorationBoardImageSrc(player.faction) ?? undefined}
                      />
                    )}
                    <small>{player?.structures.length ?? 0}개 배치</small>
                    {player && (
                      <strong className="starting-player-bid">
                        -{player.setup_bid_vp}점
                      </strong>
                    )}
                  </span>
                </div>
              );
            })}
          </section>

          <section className="faction-selection-panel starting-structure-panel">
            <div className="faction-selection-prompt">
              {isMyTurn
                ? `${homePlanet} 행성을 눌러 ${structure}을(를) 배치하세요.`
                : `${playerLabel(placement.active_player)}님이 ${structure}을(를) 배치하는 중입니다.`}
            </div>
            <div className="starting-placement-meta">
              <span>단계 {placement.placement_index + 1}</span>
              <span>{activeFaction}</span>
              <strong>{structure}</strong>
            </div>
            <div className="starting-placement-controls">
              <span>
                {selectedHex
                  ? `배치 좌표: (${selectedHex.q}, ${selectedHex.r})`
                  : isMyTurn
                    ? `노란 테두리의 ${homePlanet} 행성을 선택하세요.`
                    : '현재 플레이어의 배치를 기다리고 있습니다.'}
              </span>
              <button
                type="button"
                className="btn btn-primary"
                disabled={!isMyTurn || selectedHex === null}
                onClick={onConfirm}
              >
                {structure} 배치 확정
              </button>
            </div>
            {validTargets.length === 0 && (
              <p className="error-msg">배치할 수 있는 홈 행성이 없습니다.</p>
            )}
            {errorMessage && <p className="error-msg">{errorMessage}</p>}
          </section>
        </div>
      </aside>
    </div>
  );
}

interface StartingBoosterSetupProps {
  game: GameState;
  selection: StartingBoosterPhase;
  isMyTurn: boolean;
  isConnected: boolean;
  selectedBooster: number | null;
  errorMessage: string | null;
  playerLabel: (id: PlayerId) => string;
  emphasizeStructures: boolean;
  onSelectBooster: (boosterId: number) => void;
  onConfirm: () => void;
}

function StartingBoosterSetup({
  game,
  selection,
  isMyTurn,
  isConnected,
  selectedBooster,
  errorMessage,
  playerLabel,
  emphasizeStructures,
  onSelectBooster,
  onConfirm,
}: StartingBoosterSetupProps) {
  const selectionOrder = [...game.turn_order].reverse();

  return (
    <div className="app app--game setup-game-preview">
      <nav className="game-topbar" aria-label="초기 설정 상태">
        <span className="game-top-control setup-phase-indicator">테란 초기 설정 · 부스터 선택</span>
      </nav>
      <aside className="game-reference-rail" aria-label="게임 참조 보드">
        <section className="game-reference-card">
          <h2>연구 트랙</h2>
          <ResearchBoard players={game.players} board={game.research_board} />
        </section>
        <section className="game-ship-list" aria-label="함선 보드 영역">
          <h2>함선 보드</h2>
          <SpaceshipBoards spaceshipBoards={game.spaceship_boards} players={game.players} />
        </section>
      </aside>
      <main className="game-board-stage">
        <GameBoard
          board={game.board}
          players={game.players}
          emphasizeStructures={emphasizeStructures}
        />
        <LostFleetTechRequirementBoard
          side={game.research_board.lost_fleet_advanced_tech_requirement}
          tileId={game.research_board.lost_fleet_advanced_tech_tile}
        />
      </main>
      <aside className="game-sidebar setup-booster-sidebar" style={{ overflowY: 'auto' }}>
        <div className="faction-selection-view starting-booster-view">
            <SetupHeader kicker="REVERSE TURN ORDER" title="초기 부스터 선택" isConnected={isConnected} />

            <section className="faction-selection-order" aria-label="초기 부스터 선택 순서">
              {selectionOrder.map((id, index) => {
                const player = game.players.find((candidate) => candidate.player_id === id);
                const isActive = id === selection.active_player;
                const selected = player?.booster ?? null;
                return (
                  <div
                    key={id}
                    className={`faction-selection-player ${isActive ? 'active' : ''} ${selected !== null ? 'complete' : ''}`}
                  >
                    <span className="faction-selection-position">{index + 1}</span>
                    <div className="starting-booster-player-identity">
                      <strong>{playerLabel(id)}</strong>
                      {player?.faction && <small>{player.faction}</small>}
                      {player && (
                        <small className="starting-booster-player-bid">
                          비딩 -{player.setup_bid_vp}점
                        </small>
                      )}
                    </div>
                    <div className="starting-booster-player-choice">
                      {selected === null ? (
                        <span>{isActive ? '선택 중' : '대기'}</span>
                      ) : (
                        <>
                          {roundBoosterImageSrc(selected) && (
                            <img
                              src={roundBoosterImageSrc(selected) ?? undefined}
                              alt={`${playerLabel(id)} · ${player?.faction ?? '종족 미정'} · 부스터 #${selected}`}
                            />
                          )}
                          <strong>부스터 #{selected}</strong>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </section>

            <section className="faction-selection-panel starting-booster-panel">
              <div className="faction-selection-prompt">
                {isMyTurn
                  ? '이번 라운드에 사용할 부스터 하나를 선택하세요.'
                  : `${playerLabel(selection.active_player)}님이 부스터를 선택하는 중입니다.`}
              </div>
              <div className="starting-booster-grid">
                {game.boosters.map((boosterId) => {
                  const imageSrc = roundBoosterImageSrc(boosterId);
                  const selected = selectedBooster === boosterId;
                  return (
                    <button
                      key={boosterId}
                      type="button"
                      className={`starting-booster-choice ${selected ? 'selected' : ''}`}
                      disabled={!isMyTurn}
                      aria-label={`부스터 #${boosterId} 선택`}
                      aria-pressed={selected}
                      onClick={() => onSelectBooster(boosterId)}
                    >
                      {imageSrc && <img src={imageSrc} alt="" />}
                      <strong>부스터 #{boosterId}</strong>
                    </button>
                  );
                })}
              </div>
              <button
                type="button"
                className="btn btn-primary starting-booster-confirm"
                disabled={!isMyTurn || selectedBooster === null}
                onClick={onConfirm}
              >
                부스터 선택 확정
              </button>
              {errorMessage && <p className="error-msg">{errorMessage}</p>}
            </section>
        </div>
      </aside>
    </div>
  );
}

interface BiddingSetupProps {
  bidding: BiddingState;
  actor: PlayerId | null;
  isMyTurn: boolean;
  myVp: number;
  bidAmount: number;
  selectedFaction: FactionId | null;
  selectedTurnPosition: number | null;
  isConnected: boolean;
  errorMessage: string | null;
  playerLabel: (id: PlayerId) => string;
  terraformingColorOrder: PlanetType[];
  onBidAmountChange: (amount: number) => void;
  onSelectFaction: (faction: FactionId) => void;
  onSelectTurnPosition: (position: number) => void;
  onPlaceBid: () => void;
  onPass: () => void;
  onConfirmChoice: () => void;
}

function BiddingSetup({
  bidding,
  actor,
  isMyTurn,
  myVp,
  bidAmount,
  selectedFaction,
  selectedTurnPosition,
  isConnected,
  errorMessage,
  playerLabel,
  terraformingColorOrder,
  onBidAmountChange,
  onSelectFaction,
  onSelectTurnPosition,
  onPlaceBid,
  onPass,
  onConfirmChoice,
}: BiddingSetupProps) {
  const winnerChoice = bidding.stage !== 'Auction' && bidding.stage !== 'Complete'
    ? bidding.stage.WinnerChoice
    : null;
  const assignmentFor = (player: PlayerId): BidAssignment | undefined =>
    bidding.assignments.find((assignment) => assignment.player === player);
  const canPlaceBid =
    isMyTurn &&
    bidding.stage === 'Auction' &&
    Number.isInteger(bidAmount) &&
    bidAmount > bidding.highest_bid &&
    bidAmount <= MAX_BID;

  return (
    <div className="faction-selection-view bidding-view">
      <SetupHeader kicker="시계방향 승점 경매" title="종족 비딩" isConnected={isConnected} />

      <TerraformingSelectionBoard colorOrder={terraformingColorOrder} />

      <section className="faction-selection-order" aria-label="비딩 참가 순서">
        {bidding.clockwise_order.map((id, index) => {
          const assignment = assignmentFor(id);
          const isActive = actor === id;
          const hasPassed = bidding.passed_players.includes(id);
          return (
            <div
              key={id}
              className={`faction-selection-player ${isActive ? 'active' : ''} ${assignment ? 'complete' : ''} ${hasPassed ? 'passed' : ''}`}
            >
              <span className="faction-selection-position">{index + 1}</span>
              <strong>{playerLabel(id)}</strong>
              <span>
                {assignment ? (
                  <span className="bidding-assignment">
                    <FactionBadge
                      faction={assignment.faction}
                      size={28}
                      imageSrc={explorationBoardImageSrc(assignment.faction) ?? undefined}
                    />
                    <small>순서 {assignment.turn_position} · 승점 -{assignment.bid_vp}점</small>
                  </span>
                ) : hasPassed ? (
                  '패스'
                ) : isActive ? (
                  winnerChoice ? '선택 중' : '입찰 중'
                ) : (
                  '대기'
                )}
              </span>
            </div>
          );
        })}
      </section>

      {bidding.stage === 'Auction' ? (
        <section className="faction-selection-panel bidding-panel">
          <div className="bidding-summary" aria-label="현재 입찰 상태">
            <div>
              <span>현재 최고 입찰</span>
              <strong>승점 {bidding.highest_bid}점</strong>
            </div>
            <div>
              <span>최고 입찰자</span>
              <strong>
                {bidding.highest_bidder === null
                  ? '없음'
                  : playerLabel(bidding.highest_bidder)}
              </strong>
            </div>
            <div>
              <span>현재 보유 승점</span>
              <strong>승점 {myVp}점</strong>
            </div>
          </div>
          <div className="faction-selection-prompt">
            {isMyTurn
              ? '현재 최고 입찰보다 높은 승점을 제시하거나 패스하세요.'
              : `${actor === null ? '경매 종료' : playerLabel(actor)}님의 결정을 기다리는 중입니다.`}
          </div>
          <div className="bidding-controls">
            <label htmlFor="bid-amount">입찰 승점</label>
            <input
              id="bid-amount"
              type="number"
              min={bidding.highest_bid + 1}
              max={MAX_BID}
              step={1}
              value={bidAmount}
              disabled={!isMyTurn}
              onChange={(event) => onBidAmountChange(Number(event.target.value))}
            />
            <button className="btn btn-primary" disabled={!canPlaceBid} onClick={onPlaceBid}>
              승점 {bidAmount}점 입찰
            </button>
            <button className="btn btn-secondary" disabled={!isMyTurn} onClick={onPass}>
              패스
            </button>
          </div>
          <p className="bidding-rule-note">입찰 승점은 게임 도중 유지되고 최종 점수에서 차감됩니다.</p>
          {errorMessage && <p className="error-msg">{errorMessage}</p>}
        </section>
      ) : winnerChoice ? (
        <section className="faction-selection-panel bidding-panel">
          <div className="faction-selection-prompt">
            {isMyTurn
              ? `승점 ${winnerChoice.bid_vp}점으로 낙찰되었습니다. 종족과 최종 순서를 선택하세요.`
              : `${playerLabel(winnerChoice.winner)}님이 종족과 순서를 선택하는 중입니다.`}
          </div>
          <div className="bidding-choice-heading">종족</div>
          <div className="faction-selection-grid">
            {bidding.available_factions.map((faction) => (
              <FactionChoice
                key={faction}
                faction={faction}
                selected={selectedFaction === faction}
                disabled={!isMyTurn}
                onClick={() => onSelectFaction(faction)}
              />
            ))}
          </div>
          <div className="bidding-choice-heading">최종 턴 순서</div>
          <div className="turn-position-grid">
            {bidding.available_turn_positions.map((position) => (
              <button
                key={position}
                type="button"
                className={selectedTurnPosition === position ? 'selected' : ''}
                disabled={!isMyTurn}
                onClick={() => onSelectTurnPosition(position)}
              >
                {position}번
              </button>
            ))}
          </div>
          <button
            className="btn btn-primary bidding-confirm"
            disabled={!isMyTurn || selectedFaction === null || selectedTurnPosition === null}
            onClick={onConfirmChoice}
          >
            종족과 순서 확정
          </button>
          {errorMessage && <p className="error-msg">{errorMessage}</p>}
        </section>
      ) : null}
    </div>
  );
}

function SetupHeader({
  kicker,
  title,
  isConnected,
}: {
  kicker: string;
  title: string;
  isConnected: boolean;
}) {
  return (
    <header className="faction-selection-header">
      <div>
        <p className="faction-selection-kicker">{kicker}</p>
        <h2>{title}</h2>
      </div>
      <div className="connection-status">
        <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
        <span>{isConnected ? '연결됨' : '연결 중...'}</span>
      </div>
    </header>
  );
}

function FactionChoice({
  faction,
  selected = false,
  disabled,
  onClick,
}: {
  faction: FactionId;
  selected?: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`faction-selection-choice ${selected ? 'selected' : ''}`}
      disabled={disabled}
      onClick={onClick}
      aria-label={`${faction} 선택`}
      aria-pressed={selected}
    >
      <FactionBadge
        faction={faction}
        size={54}
        imageSrc={explorationBoardImageSrc(faction) ?? undefined}
      />
    </button>
  );
}
