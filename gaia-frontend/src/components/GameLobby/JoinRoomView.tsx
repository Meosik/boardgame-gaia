import { useEffect, useState } from 'react';
import { useRoomStore } from '../../store/roomStore';
import { api } from '../../api/rest';
import type { RoomSummary } from '../../types/game';

interface Props {
  onRoomJoined: () => void;
  onBack: () => void;
}

export function JoinRoomView({ onRoomJoined, onBack }: Props) {
  const [code, setCode] = useState('');
  const [nickname, setNickname] = useState('');
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

  async function handleJoin(joinCode: string) {
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
      await joinRoom(joinCode.trim().toUpperCase(), nickname.trim());
      onRoomJoined();
    } catch (e) {
      setError(e instanceof Error ? e.message : '참가에 실패했습니다');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="join-room-view">
      <h2>방 참가하기</h2>

      <div className="form-group">
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

      <div className="room-list" aria-label="참가 가능한 방 목록">
        <h3>참가 가능한 방</h3>
        {roomsError ? (
          <p className="error-msg">{roomsError}</p>
        ) : rooms === null ? (
          <p className="preview-loading">방 목록을 불러오는 중...</p>
        ) : rooms.length === 0 ? (
          <p>지금 대기 중인 방이 없습니다. 룸 코드로 직접 참가해보세요.</p>
        ) : (
          <ul className="room-list-items">
            {rooms.map((room) => (
              <li key={room.code} className="room-list-item">
                <span className="mono">{room.code}</span>
                <span>{room.host_nickname}님의 방</span>
                <span>{room.player_count}/4</span>
                <button
                  type="button"
                  className="btn btn-small btn-secondary"
                  disabled={loading}
                  onClick={() => { setCode(room.code); void handleJoin(room.code); }}
                >
                  참가
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="form-group">
        <label htmlFor="room-code">룸 코드</label>
        <input
          id="room-code"
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          maxLength={8}
          placeholder="XXXXXX"
          className="mono"
        />
      </div>

      {error && <p className="error-msg">{error}</p>}

      <div className="form-actions">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>
          뒤로
        </button>
        <button className="btn btn-primary" onClick={() => void handleJoin(code)} disabled={loading}>
          {loading ? '참가 중...' : '참가하기'}
        </button>
      </div>
    </div>
  );
}
