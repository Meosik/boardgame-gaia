import { useState } from 'react';
import { api } from '../api/rest';
import { useRoomStore } from '../store/roomStore';
import { forgetRecentRoom } from '../store/recentRoom';

export function DevTestControls({ refillDisabled }: { refillDisabled: boolean }) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  async function run(tool: 'refill' | 'delete') {
    if (busy) return;
    const room = useRoomStore.getState();
    if (!room.manualControl || !room.roomCode || !room.sessionToken) return;
    setBusy(true);
    setNotice('');
    try {
      await api.devTool(room.roomCode, room.sessionToken, room.revision, tool);
      if (tool === 'delete') {
        forgetRecentRoom(room.roomCode);
        room.actions.reset();
        window.location.assign('/?devGame=1');
      } else {
        setNotice('전원 자원 250 · 파워 I/II/III 각 10개 적용');
      }
    } catch {
      setNotice('처리하지 못했습니다. 연결 상태를 확인하고 다시 눌러 주세요.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button type="button" disabled={busy || refillDisabled} onClick={() => void run('refill')}
        title="전원 광석·크레딧·지식·QIC 250, 파워 I·II·III 각 10개. 가이아는 유지">
        테스트 자원 보충
      </button>
      <button type="button" disabled={busy} onClick={() => void run('delete')}
        title="현재 테스트 방과 저장 기록을 즉시 삭제하고 로비로 이동합니다">
        테스트 방 삭제
      </button>
      {notice && <span role="status">{notice}</span>}
    </>
  );
}
