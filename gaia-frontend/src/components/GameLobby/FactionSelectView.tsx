import { useEffect, useMemo, useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { useGameStore } from '../../store/gameStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { FactionBadge } from './FactionBadge';
import { factionBoardImageSrc } from '../../assets/factionBoardImages';
import type {
  FactionAssignment,
  FactionId,
  FactionSelectionState,
  PlayerId,
} from '../../types/game';
import { isGameState } from '../../types/game';

interface Props {
  onGameStart: () => void;
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

export function FactionSelectView({ onGameStart }: Props) {
  const { roomCode, sessionToken, nickname, gameSetup, playerId, lobbyPlayers, revision, setRevision } =
    useRoomStore((state) => ({
      roomCode: state.roomCode!,
      sessionToken: state.sessionToken,
      nickname: state.nickname,
      gameSetup: state.gameSetup,
      playerId: state.playerId,
      lobbyPlayers: state.lobbyPlayers,
      revision: state.revision,
      setRevision: state.actions.setRevision,
    }));
  const setGameState = useGameStore((state) => state.actions.setGameState);
  const { isConnected, send, sendCommand, lastMessage } = useWebSocket(roomCode);
  const [selectionState, setSelectionState] = useState<FactionSelectionState | null>(null);

  const playerNames = useMemo(
    () => new Map(lobbyPlayers.map((player) => [player.player_id, player.nickname])),
    [lobbyPlayers],
  );
  const initialState = useMemo(
    () =>
      initialSelectionState(
        lobbyPlayers.map((player) => player.player_id),
        gameSetup?.factions ?? [],
      ),
    [gameSetup?.factions, lobbyPlayers],
  );
  const state = selectionState ?? initialState;
  const activePlayer = state.player_order[state.current_index] ?? null;
  const isMyTurn = playerId !== null && activePlayer === playerId;

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

  useEffect(() => {
    if (!lastMessage) return;
    switch (lastMessage.type) {
      case 'room_joined':
      case 'command_accepted':
        setRevision(lastMessage.revision);
        break;
      case 'snapshot': {
        setRevision(lastMessage.revision);
        const { state } = lastMessage;
        if (!isGameState(state)) break;
        if (state.faction_selection) {
          setSelectionState(state.faction_selection);
        }
        // `faction_selection` clears once setup completes and `phase` moves
        // past `Setup` — that's when gameplay actually starts.
        if (!(typeof state.phase === 'object' && 'Setup' in state.phase)) {
          setGameState(state);
          onGameStart();
        }
        break;
      }
    }
  }, [lastMessage, onGameStart, setGameState, setRevision]);

  function selectFaction(faction: FactionId) {
    if (!isMyTurn) return;
    sendCommand({ type: 'place_setup_action', action: { type: 'SelectFaction', faction } }, revision);
  }

  function playerLabel(id: PlayerId) {
    return playerNames.get(id) ?? `P${id}`;
  }

  function assignmentFor(player: PlayerId): FactionAssignment | undefined {
    return state.assignments.find((assignment) => assignment.player === player);
  }

  return (
    <div className="faction-selection-view">
      <header className="faction-selection-header">
        <div>
          <p className="faction-selection-kicker">OFFICIAL CLOCKWISE SETUP</p>
          <h2>종족 선택</h2>
        </div>
        <div className="connection-status">
          <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          <span>{isConnected ? '연결됨' : '연결 중...'}</span>
        </div>
      </header>

      <section className="faction-selection-order" aria-label="종족 선택 순서">
        {state.player_order.map((id, index) => {
          const assignment = assignmentFor(id);
          const isActive = index === state.current_index;
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
                    imageSrc={factionBoardImageSrc(assignment.faction) ?? undefined}
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
          {state.available_factions.map((faction) => (
            <button
              key={faction}
              type="button"
              className="faction-selection-choice"
              disabled={!isMyTurn}
              onClick={() => selectFaction(faction)}
              aria-label={`${faction} 선택`}
            >
              <FactionBadge
                faction={faction}
                size={54}
                imageSrc={factionBoardImageSrc(faction) ?? undefined}
              />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}
