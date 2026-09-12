import { useEffect, useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { api } from '../../api/rest';
import { LOST_FLEET_DISPLAY_NAME } from '../../displayNames';
import type { RoomSummary } from '../../types/game';

interface Props {
  onRoomJoined: () => void;
  onCreateRoom: () => void;
  recentRoomCode?: string;
  onResumeRoom?: () => void;
}

const SETUP_MODE_LABELS = { bidding: '승점 비딩', sequential: '순차 선택' } as const;

/** The lobby's front page: the open rooms as a card grid, with the tutorial and the AI replay as
 * full-width entries underneath rather than small buttons in the corner. Joining by code stays as
 * a compact fallback — the room list covers the normal case, but a room that has already started
 * is not listed and someone may have been handed nothing but a code. */
export function LobbyHomeView({ onRoomJoined, onCreateRoom, recentRoomCode, onResumeRoom }: Props) {
  const [code, setCode] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [lockedRoom, setLockedRoom] = useState<RoomSummary | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [rooms, setRooms] = useState<RoomSummary[] | null>(null);
  const [roomsError, setRoomsError] = useState('');
  const joinRoom = useRoomStore((s) => s.actions.joinRoom);

  useEffect(() => {
    let cancelled = false;
    api.listRooms()
      .then((list) => { if (!cancelled) setRooms(list); })
      .catch(() => { if (!cancelled) setRoomsError('방 목록을 불러오지 못했습니다'); });
    return () => { cancelled = true; };
  }, []);

  async function handleJoin(joinCode: string, roomPassword?: string) {
    if (!joinCode.trim()) {
      setError('룸 코드를 입력해주세요');
      return;
    }
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await joinRoom(joinCode.trim().toUpperCase(), nickname.trim(), undefined, roomPassword?.trim() || undefined);
      onRoomJoined();
    } catch (e) {
      setError(e instanceof Error ? e.message : '참가에 실패했습니다');
    } finally {
      setLoading(false);
    }
  }

  /** A locked room asks for its password first; an open one joins straight away. */
  function selectRoom(room: RoomSummary) {
    setError('');
    setCode(room.code);
    if (room.has_password) {
      setPassword('');
      setLockedRoom(room);
      return;
    }
    setLockedRoom(null);
    void handleJoin(room.code);
  }

  return (
    <div className="lobby-home-view">
      <header className="lobby-home-header">
        <div>
          <h1 className="game-title">Gaia Project</h1>
          <p className="game-subtitle">{LOST_FLEET_DISPLAY_NAME} 에디션 · 4인</p>
        </div>
        <div className="lobby-home-actions">
          {recentRoomCode && onResumeRoom && (
            <button className="btn btn-secondary" onClick={onResumeRoom}>
              이어하기 · {recentRoomCode}
            </button>
          )}
          <button className="btn btn-primary" onClick={onCreateRoom}>방 만들기</button>
        </div>
      </header>

      <div className="form-group lobby-nickname">
        <label htmlFor="nickname">닉네임</label>
        <input
          id="nickname"
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          maxLength={16}
          placeholder="닉네임 입력"
        />
      </div>

      <div className="room-list" aria-label="참가 가능한 방">
        <h3>참가 가능한 방</h3>
        {roomsError ? (
          <p className="error-msg">{roomsError}</p>
        ) : rooms === null ? (
          <p className="preview-loading">방 목록을 불러오는 중...</p>
        ) : rooms.length === 0 ? (
          <p className="room-list-empty">지금 대기 중인 방이 없습니다. 방을 만들거나 룸 코드로 참가해보세요.</p>
        ) : (
          <ul className="room-grid">
            {rooms.map((room) => (
              <li key={room.code} className="room-card">
                <span className="room-list-name">
                  {room.has_password && <span aria-label="비밀번호가 있는 방" title="비밀번호가 있는 방">🔒</span>}
                  {room.name}
                </span>
                <span className="room-list-host">{room.host_nickname}</span>
                <span className="room-card-meta">
                  <span className="mono">{room.code}</span>
                  <span className="room-card-seats">{room.player_count}/4</span>
                  {room.setup_mode && <span className="room-list-mode">{SETUP_MODE_LABELS[room.setup_mode]}</span>}
                </span>
                <button
                  type="button"
                  className="btn btn-small btn-secondary room-card-join"
                  disabled={loading}
                  onClick={() => selectRoom(room)}
                >
                  참가
                </button>
              </li>
            ))}
          </ul>
        )}

        {lockedRoom && (
          <div className="form-group room-password-prompt">
            <label htmlFor="room-password">{lockedRoom.name} · 비밀번호</label>
            <input
              id="room-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              maxLength={32}
              placeholder="방 비밀번호"
              onKeyDown={(e) => { if (e.key === 'Enter') void handleJoin(lockedRoom.code, password); }}
            />
            <button
              type="button"
              className="btn btn-primary"
              disabled={loading}
              onClick={() => void handleJoin(lockedRoom.code, password)}
            >
              {loading ? '참가 중...' : '비밀번호 확인'}
            </button>
          </div>
        )}
      </div>

      {error && <p className="error-msg">{error}</p>}

      <div className="lobby-code-join">
        <label htmlFor="room-code">룸 코드로 참가</label>
        <input
          id="room-code"
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          maxLength={8}
          placeholder="XXXXXX"
          className="mono"
        />
        <button
          className="btn btn-small btn-secondary"
          onClick={() => void handleJoin(code, lockedRoom?.code === code ? password : undefined)}
          disabled={loading}
        >
          {loading ? '참가 중...' : '참가하기'}
        </button>
      </div>

      <div className="lobby-entries">
        <a className="lobby-entry" href="?tutorial=1">
          <span className="lobby-entry-title">튜토리얼</span>
          <span className="lobby-entry-desc">행동 설명과 첫 게임 따라 하기</span>
        </a>
        <a className="lobby-entry" href="?aiReplay=1">
          <span className="lobby-entry-title">AI 보기</span>
          <span className="lobby-entry-desc">AI끼리 둔 대국을 처음부터 되돌려 봅니다</span>
        </a>
      </div>
    </div>
  );
}
