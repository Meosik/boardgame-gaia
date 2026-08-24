import { useEffect, useState } from 'react';
import { GameLobby } from './components/GameLobby';
import { GameBoard } from './components/GameBoard';
import { PlayerDashboard } from './components/PlayerDashboard';
import { ActionPanel } from './components/ActionPanel';
import { useGameStore } from './store/gameStore';
import { useRoomStore } from './store/roomStore';
import { GaiaWebSocket } from './api/websocket';
import type { ServerMessage } from './types/game';
import { isGameState } from './types/game';

type AppView = 'lobby' | 'game';

export function App() {
  const [view, setView] = useState<AppView>('lobby');

  const { roomCode, playerId, sessionToken, nickname, lastError, actions: roomActions } = useRoomStore((s) => ({
    roomCode: s.roomCode,
    playerId: s.playerId,
    sessionToken: s.sessionToken,
    nickname: s.nickname,
    lastError: s.lastError,
    actions: s.actions,
  }));

  const { gameState, myPlayerId, actions: gameActions } = useGameStore((s) => ({
    gameState: s.gameState,
    myPlayerId: s.myPlayerId,
    actions: s.actions,
  }));

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
        default:
          break;
      }
    });

    client.connect();
    // Re-join on this fresh connection using the session established in the
    // lobby — `send` queues until the socket is open, no need to wait here.
    client.send({ type: 'join_room', room_code: roomCode, nickname, session_token: sessionToken });

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

  function handleGameStart() {
    setView('game');
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

  return (
    <div className="app app--game">
      {lastError && (
        <div className="error-banner" onClick={() => roomActions.setError(null)}>
          {lastError.message} ({lastError.code})
        </div>
      )}
      <PlayerDashboard players={gameState.players} />
      <div className="game-main">
        <GameBoard board={gameState.board} players={gameState.players} />
        <div className="game-sidebar">
          <ActionPanel gameState={gameState} myPlayerId={myId} />
        </div>
      </div>
    </div>
  );
}
