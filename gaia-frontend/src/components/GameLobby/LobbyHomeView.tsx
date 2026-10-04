import { useEffect, useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { api } from '../../api/rest';
import { LOST_FLEET_DISPLAY_NAME } from '../../displayNames';
import type { RoomSummary } from '../../types/game';

interface Props {
  onRoomJoined: () => void;
  onCreateRoom: () => void;
  onTutorialStart?: () => void;
  recentRoomCode?: string;
  onResumeRoom?: () => void;
}

const SETUP_MODE_LABELS = { bidding: '승점 비딩', sequential: '순차 선택' } as const;

/** The lobby's front page: the open rooms as a card grid, with the tutorial and the AI replay as
 * full-width entries underneath. Every waiting room is listed, so picking one from the list is the
 * only way in — typing a code would just be a slower way to reach the same rooms, and reconnecting
 * to a game already in progress is what the 이어하기 shortcut is for. */
export function LobbyHomeView({ onRoomJoined, onCreateRoom, onTutorialStart, recentRoomCode, onResumeRoom }: Props) {
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
    if (!nickname.trim()) {
      setError('닉네임을 입력해주세요');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await joinRoom(joinCode, nickname.trim(), undefined, roomPassword?.trim() || undefined);
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
          <p className="room-list-empty">지금 대기 중인 방이 없습니다. 위의 방 만들기로 첫 방을 열어보세요.</p>
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

      <div className="lobby-entries">
        <div className="lobby-entry">
          <span className="lobby-entry-title">튜토리얼</span>
          <button type="button" className="btn btn-primary" disabled={loading} onClick={async () => {
            setLoading(true);
            setError('');
            try { await useRoomStore.getState().actions.createTutorialGame(); onTutorialStart?.(); }
            catch (e) { setError(e instanceof Error ? e.message : '튜토리얼을 시작하지 못했습니다'); }
            finally { setLoading(false); }
          }}>1라운드 따라 하기</button>
          <a href="?tutorial=1">행동 설명 보기</a>
        </div>
        <a className="lobby-entry" href="?aiReplay=1">
          <span className="lobby-entry-title">AI 보기</span>
          <span className="lobby-entry-desc">AI끼리 둔 대국을 처음부터 되돌려 봅니다</span>
        </a>
      </div>
    </div>
  );
}
