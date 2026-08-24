import { useEffect, useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { isGameState } from '../../types/game';

type SeedResult =
  | { ok: true; seed: string | undefined }
  | { ok: false; error: string };

/** 빈 입력 → ok(seed undefined) / URL+seed파라미터 → ok(seed) / URL인데 seed없음 → error / 일반문자열 → ok(seed) */
function parseSeed(input: string): SeedResult {
  const trimmed = input.trim();
  if (!trimmed) return { ok: true, seed: undefined };
  try {
    const url = new URL(trimmed);
    const seed = url.searchParams.get('seed');
    if (!seed) return { ok: false, error: 'URL에 seed 파라미터가 없습니다 (예: ?seed=abc123)' };
    return { ok: true, seed };
  } catch {
    return { ok: true, seed: trimmed };
  }
}

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
    lobbyPlayers,
    hostPlayerId,
    revision,
    actions,
  } = useRoomStore((s) => ({
    roomCode: s.roomCode!,
    playerId: s.playerId,
    sessionToken: s.sessionToken,
    playerCount: s.playerCount,
    nickname: s.nickname,
    gameSetup: s.gameSetup,
    lobbyPlayers: s.lobbyPlayers,
    hostPlayerId: s.hostPlayerId,
    revision: s.revision,
    actions: s.actions,
  }));

  const { isConnected, send, sendCommand, lastMessage } = useWebSocket(roomCode);
  const [seedInput, setSeedInput] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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

  useEffect(() => {
    if (!lastMessage) return;
    switch (lastMessage.type) {
      case 'player_joined':
        actions.setRoomInfo({ playerCount: lastMessage.player_count });
        break;
      case 'lobby_state':
        actions.setRoomInfo({
          lobbyPlayers: lastMessage.players,
          playerCount: lastMessage.players.length,
          hostPlayerId: lastMessage.host_player_id,
        });
        break;
      case 'room_joined':
        actions.setRoomInfo({ gameSetup: lastMessage.game_setup });
        actions.setRevision(lastMessage.revision);
        break;
      case 'command_accepted':
        actions.setRevision(lastMessage.revision);
        break;
      case 'snapshot': {
        actions.setRevision(lastMessage.revision);
        const { state } = lastMessage;
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
        setErrorMsg(lastMessage.rejection.message_key);
        break;
      case 'error':
        setErrorMsg(lastMessage.message);
        break;
    }
  }, [lastMessage]);

  const isHost = playerId !== null && playerId === hostPlayerId;
  const me = lobbyPlayers.find((player) => player.player_id === playerId);
  const isReady = me?.ready ?? false;
  const hasReadyPlayers = lobbyPlayers.some((player) => player.ready);

  function handleApplySeed() {
    const result = parseSeed(seedInput);
    if (!result.ok) {
      setErrorMsg(result.error);
      return;
    }
    setErrorMsg(null);
    sendCommand({ type: 'regenerate_setup', seed: result.seed }, revision);
  }

  function handleToggleReady() {
    sendCommand({ type: 'player_ready', ready: !isReady }, revision);
  }

  function handleRegenerateSetup() {
    void actions.regenerateSetup();
  }

  return (
    <div className="waiting-room-view">
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
          <span>시드: </span>
          <span className="mono">{gameSetup.seed}</span>
        </div>
      )}
      {isHost && (
        <div className="form-group seed-input-group">
          <label>시드 변경 (URL 또는 시드 문자열)</label>
          <div className="seed-input-row">
            <input
              type="text"
              value={seedInput}
              onChange={(e) => { setSeedInput(e.target.value); setErrorMsg(null); }}
              onKeyDown={(e) => e.key === 'Enter' && handleApplySeed()}
              placeholder="uiqoo.kr/?seed=... 또는 시드 직접 입력"
            />
            <button className="btn btn-primary btn-small" onClick={handleApplySeed}>
              적용
            </button>
            <button
              className="btn btn-secondary btn-small"
              onClick={handleRegenerateSetup}
              disabled={hasReadyPlayers}
            >
              랜더마이저 재설정
            </button>
          </div>
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
        {playerCount < 2
          ? '게임을 시작하려면 최소 2명이 필요합니다.'
          : lobbyPlayers.every((player) => player.ready)
          ? '비딩을 시작하는 중...'
          : '모든 플레이어가 준비 완료하기를 기다리는 중...'}
      </div>
    </div>
  );
}
