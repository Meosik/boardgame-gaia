import { useState } from 'react';
import { useRoomStore } from '../../store/roomStore';

interface Props {
  onRoomJoined: () => void;
  onBack: () => void;
}

export function JoinRoomView({ onRoomJoined, onBack }: Props) {
  const [code, setCode] = useState('');
  const [nickname, setNickname] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const joinRoom = useRoomStore((s) => s.actions.joinRoom);

  async function handleJoin() {
    if (!code.trim()) {
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
      await joinRoom(code.trim().toUpperCase(), nickname.trim());
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

      {error && <p className="error-msg">{error}</p>}

      <div className="form-actions">
        <button className="btn btn-ghost" onClick={onBack} disabled={loading}>
          뒤로
        </button>
        <button className="btn btn-primary" onClick={handleJoin} disabled={loading}>
          {loading ? '참가 중...' : '참가하기'}
        </button>
      </div>
    </div>
  );
}
