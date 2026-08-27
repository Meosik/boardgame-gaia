import { useEffect, useRef, useState } from 'react';
import { shallow } from 'zustand/shallow';
import { useRoomStore } from '../../store/roomStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { isGameState } from '../../types/game';
import { GameBoard } from '../GameBoard';
import { ScoringBoard } from '../ScoringBoard';
import { RoundBoosters } from '../RoundBoosters';
import { SpaceshipBoards } from '../SpaceshipBoards';
import { BoardOverlay } from '../BoardOverlay';
import { FloatingBoardPanel } from '../FloatingBoardPanel';
import { ResearchBoard } from '../PlayerDashboard/ResearchBoard';

interface Props {
  onGameStart: () => void;
  onFactionSelect: () => void;
}

export function WaitingRoomView({ onGameStart, onFactionSelect }: Props) {
  const {
    roomCode,
    playerId,
    sessionToken,
    playerCount,
    nickname,
    gameSetup,
    previewBoard,
    lobbyPlayers,
    hostPlayerId,
    revision,
    actions,
  } = useRoomStore(
    (s) => ({
      roomCode: s.roomCode!,
      playerId: s.playerId,
      sessionToken: s.sessionToken,
      playerCount: s.playerCount,
      nickname: s.nickname,
      gameSetup: s.gameSetup,
      previewBoard: s.previewBoard,
      lobbyPlayers: s.lobbyPlayers,
      hostPlayerId: s.hostPlayerId,
      revision: s.revision,
      actions: s.actions,
    }),
    shallow,
  );

  const { isConnected, send, sendCommand, messages } = useWebSocket(roomCode);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [activeOverlay, setActiveOverlay] = useState<'scoring' | 'boosters' | 'spaceships' | null>(null);

  useEffect(() => {
    if (isConnected && sessionToken) {
      send({
        type: 'join_room',
        room_code: roomCode,
        nickname,
        session_token: sessionToken,
      });
    }
  }, [isConnected]);

  // Re-fetches whenever `gameSetup.seed` changes — the reroll button already
  // updates `gameSetup` (and therefore `.seed`) through its existing REST
  // call, so this is the single hook point needed to keep the backdrop in
  // sync with the current setup.
  useEffect(() => {
    if (gameSetup?.seed) {
      void actions.fetchPreviewBoard();
    }
  }, [gameSetup?.seed]);

  // Processes every message that arrived since the last run, in order —
  // NOT just the latest. The server can broadcast several messages
  // back-to-back for one command (e.g. `handle_player_ready`'s `snapshot`
  // immediately followed by a `lobby_state`); if both land in the same
  // React batch, reacting to only "the most recent message" would silently
  // drop the earlier one — which, for exactly this pair, is the one
  // carrying the real `GameState` that signals faction selection/bidding
  // has actually started. `processedCount` tracks how far through
  // `messages` (append-only) this effect has already gotten.
  const processedCount = useRef(0);
  useEffect(() => {
    for (let i = processedCount.current; i < messages.length; i++) {
      const message = messages[i];
      switch (message.type) {
        case 'player_joined':
          actions.setRoomInfo({ playerCount: message.player_count });
          break;
        case 'lobby_state':
          actions.setRoomInfo({
            lobbyPlayers: message.players,
            playerCount: message.players.length,
            hostPlayerId: message.host_player_id,
          });
          break;
        case 'room_joined':
          actions.setRoomInfo({ gameSetup: message.game_setup });
          actions.setRevision(message.revision);
          break;
        case 'command_accepted':
          actions.setRevision(message.revision);
          break;
        case 'snapshot': {
          actions.setRevision(message.revision);
          const { state } = message;
          if (!isGameState(state)) {
            if (state.setup) actions.setRoomInfo({ gameSetup: state.setup });
            break;
          }
          // A `GameState` exists once all four seats ready up — that's
          // "faction selection started" until `phase` moves past `Setup`.
          if (typeof state.phase === 'object' && 'Setup' in state.phase) {
            actions.setRoomInfo({ roomState: 'faction_selection' });
            onFactionSelect();
          } else {
            onGameStart();
          }
          break;
        }
        case 'command_rejected':
          // A rejected command still carries the room's actual current
          // revision — without resyncing to it here, a stale-revision
          // rejection (e.g. a double-click firing two commands off the same
          // pre-update revision) leaves the client's revision permanently
          // behind, so every retry keeps failing the same way (matches
          // App.tsx/FactionSelectView.tsx, which already do this).
          actions.setRevision(message.revision);
          setErrorMsg(message.rejection.message_key);
          break;
        case 'error':
          setErrorMsg(message.message);
          break;
      }
    }
    processedCount.current = messages.length;
  }, [messages]);

  const isHost = playerId !== null && playerId === hostPlayerId;
  const me = lobbyPlayers.find((player) => player.player_id === playerId);
  const isReady = me?.ready ?? false;
  const hasReadyPlayers = lobbyPlayers.some((player) => player.ready);

  function handleToggleReady() {
    sendCommand({ type: 'player_ready', ready: !isReady }, revision);
  }

  function handleRegenerateSetup() {
    void actions.regenerateSetup();
  }

  return (
    <div className="waiting-room-view">
      {previewBoard && (
        <nav className="waiting-room-topbar" aria-label="게임 정보">
          <button
            className="waiting-room-top-control"
            onClick={() => setActiveOverlay('scoring')}
          >
            라운드·게임 종료 목표
          </button>
          <button
            className="waiting-room-top-control"
            onClick={() => setActiveOverlay('boosters')}
          >
            라운드 부스터
          </button>
          <button
            className="waiting-room-top-control"
            onClick={() => setActiveOverlay('spaceships')}
          >
            함선 보드
          </button>
        </nav>
      )}
      {previewBoard && (
        <aside className="waiting-room-board-rail" aria-label="게임 참조 보드">
          <section className="waiting-room-reference-card">
            <h3>연구 트랙</h3>
            <ResearchBoard players={[]} />
          </section>
          <section className="waiting-room-personal-placeholder" aria-label="개인 보드 영역">
            <strong>개인 보드 영역</strong>
            <span>종족 확정 후 종족 보드 · 자원 · 기술 · 연방 토큰이 표시됩니다.</span>
          </section>
        </aside>
      )}
      <div className="waiting-room-backdrop">
        {previewBoard ? (
          <GameBoard board={previewBoard.board} />
        ) : (
          <p className="preview-loading">보드 미리보기 불러오는 중...</p>
        )}
      </div>
      <div className="waiting-room-overlay">
        <div className="waiting-room-panel">
          <h2>대기실</h2>
          <div className="room-code-display">
            <span>룸 코드:</span>
            <span className="mono room-code">{roomCode}</span>
          </div>
          <div className="connection-status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
            {isConnected ? '연결됨' : '연결 중...'}
          </div>
          <div className="player-count">
            참가자: {playerCount} / 4명
          </div>
          <div className="lobby-player-list">
            {lobbyPlayers.map((player) => (
              <div
                key={player.player_id}
                className={`lobby-player-row ${player.ready ? 'ready' : ''}`}
              >
                <div className="lobby-player-name">
                  <span>{player.nickname}</span>
                  {player.player_id === hostPlayerId && (
                    <span className="host-badge">호스트</span>
                  )}
                  {player.player_id === playerId && (
                    <span className="me-badge">나</span>
                  )}
                </div>
                <span className="ready-state">
                  {player.ready ? '준비됨 ✓' : '대기 중'}
                </span>
              </div>
            ))}
          </div>
          {gameSetup && (
            <div className="setup-info">
              <div>
                <span>방식: </span>
                <strong>{gameSetup.setup_mode === 'bidding' ? 'VP 비딩' : '순차 선택'}</strong>
              </div>
              <div className="setup-factions-pool">
                <span>이번 게임 종족 풀: </span>
                {gameSetup.factions.map((faction) => (
                  <span key={faction} className="faction-pool-badge">{faction}</span>
                ))}
              </div>
            </div>
          )}
          {isHost && (
            <div className="form-group">
              <button
                className="btn btn-secondary btn-small"
                onClick={handleRegenerateSetup}
                disabled={hasReadyPlayers}
              >
                랜더마이저 재설정
              </button>
              {errorMsg && <p className="error-msg">{errorMsg}</p>}
            </div>
          )}
          <button
            className={`btn ${isReady ? 'btn-secondary' : 'btn-primary'} ready-toggle-btn`}
            onClick={handleToggleReady}
            disabled={!isConnected}
          >
            {isReady ? '준비 취소' : '준비 완료'}
          </button>
          <div className="waiting-hint">
            {playerCount < 4
              // `handle_player_ready` (gaia-server) only starts the game once
              // `room.player_count() == 4` — this project is always a fixed
              // 4-player game, no 2-3 player mode exists. Showing a "starting"
              // message below this threshold would be a lie: everyone could be
              // "ready" and the room would still just sit there forever.
              ? `4명이 모두 참가해야 시작할 수 있습니다 (현재 ${playerCount}/4명).`
              : lobbyPlayers.every((player) => player.ready)
              ? gameSetup?.setup_mode === 'bidding'
                ? '비딩을 시작하는 중...'
                : '종족 선택을 시작하는 중...'
              : '모든 플레이어가 준비 완료하기를 기다리는 중...'}
          </div>
        </div>
      </div>
      {activeOverlay === 'scoring' && previewBoard && (
        <BoardOverlay title="라운드·게임 종료 목표" onClose={() => setActiveOverlay(null)}>
          <ScoringBoard
            roundTiles={previewBoard.round_tiles}
            finalScoringTiles={previewBoard.final_scoring_tiles}
            currentRound={0}
          />
        </BoardOverlay>
      )}
      {activeOverlay === 'boosters' && gameSetup && (
        <BoardOverlay title="라운드 부스터" onClose={() => setActiveOverlay(null)}>
          <RoundBoosters availableBoosters={gameSetup.boosters} players={[]} />
        </BoardOverlay>
      )}
      {activeOverlay === 'spaceships' && previewBoard && (
        <FloatingBoardPanel title="함선 보드" onClose={() => setActiveOverlay(null)}>
          <SpaceshipBoards spaceshipBoards={previewBoard.spaceship_boards} players={[]} />
        </FloatingBoardPanel>
      )}
    </div>
  );
}
