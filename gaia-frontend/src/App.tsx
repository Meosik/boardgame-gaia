import { useCallback, useEffect, useState } from 'react';
import { shallow } from 'zustand/shallow';
import { GameLobby } from './components/GameLobby';
import { GameBoard } from './components/GameBoard';
import { PlayerDashboard } from './components/PlayerDashboard';
import { OpponentPanels } from './components/OpponentPanels';
import { ResearchBoard } from './components/PlayerDashboard/ResearchBoard';
import { ScoringBoard } from './components/ScoringBoard';
import { BoardOverlay } from './components/BoardOverlay';
import { FloatingBoardPanel } from './components/FloatingBoardPanel';
import { RoundBoosters } from './components/RoundBoosters';
import { SpaceshipBoards } from './components/SpaceshipBoards';
import { ActionPanel } from './components/ActionPanel';
import { GameLog } from './components/GameLog';
import { GameOverScreen } from './components/GameOverScreen';
import { useGameStore } from './store/gameStore';
import { useRoomStore } from './store/roomStore';
import { GaiaWebSocket } from './api/websocket';
import type { ServerMessage } from './types/game';
import { isGameState } from './types/game';

type AppView = 'lobby' | 'game';

export function App() {
  const [view, setView] = useState<AppView>('lobby');
  const [activeBoardOverlay, setActiveBoardOverlay] = useState<'scoring' | 'boosters' | 'spaceships' | null>(null);

  const { roomCode, playerId, sessionToken, nickname, lastError, actions: roomActions } = useRoomStore(
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

  const { gameState, myPlayerId, finalResult, actions: gameActions } = useGameStore(
    (s) => ({
      gameState: s.gameState,
      myPlayerId: s.myPlayerId,
      finalResult: s.finalResult,
      actions: s.actions,
    }),
    shallow,
  );

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
          gameActions.setFinalResult({ finalScores: msg.final_scores, winner: msg.winner });
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

  const handleGameStart = useCallback(() => {
    setView('game');
  }, []);

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
  const opponents = gameState.players.filter((p) => p.player_id !== me.player_id);

  return (
    <div className="app app--game">
      {lastError && (
        <div className="error-banner" onClick={() => roomActions.setError(null)}>
          {lastError.message} ({lastError.code})
        </div>
      )}
      <nav className="game-topbar" aria-label="게임 정보">
        <button className="game-top-control" onClick={() => setActiveBoardOverlay('scoring')}>
          라운드·게임 종료 목표
        </button>
        <button className="game-top-control" onClick={() => setActiveBoardOverlay('boosters')}>
          라운드 부스터
        </button>
        <button className="game-top-control" onClick={() => setActiveBoardOverlay('spaceships')}>
          함선 보드
        </button>
      </nav>
      <aside className="game-reference-rail" aria-label="공용 트랙과 함선 보드">
        <section className="game-reference-card">
          <h2>연구 트랙</h2>
          <ResearchBoard players={gameState.players} />
          <div className="game-vp-summary" aria-label="현재 승점">
            {gameState.players.map((player) => (
              <span key={player.player_id}>
                <strong>{player.nickname}</strong>
                <b>{player.vp} VP</b>
              </span>
            ))}
          </div>
        </section>
      </aside>
      <main className="game-board-stage">
        <GameBoard board={gameState.board} players={gameState.players} />
      </main>
      <footer className="game-personal-dock" aria-label="내 개인 보드">
        <PlayerDashboard player={me} />
      </footer>
      <aside className="game-sidebar">
        <OpponentPanels players={opponents} />
        <ActionPanel gameState={gameState} myPlayerId={myId} />
        <GameLog events={gameState.event_log ?? []} players={gameState.players} />
      </aside>
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
        <BoardOverlay title="라운드 부스터" onClose={() => setActiveBoardOverlay(null)}>
          <RoundBoosters availableBoosters={gameState.boosters} players={gameState.players} />
        </BoardOverlay>
      )}
      {activeBoardOverlay === 'spaceships' && (
        <FloatingBoardPanel title="함선 보드" onClose={() => setActiveBoardOverlay(null)}>
          <SpaceshipBoards spaceshipBoards={gameState.spaceship_boards} players={gameState.players} />
        </FloatingBoardPanel>
      )}
    </div>
  );
}
