import { LOST_FLEET_DISPLAY_NAME } from '../../displayNames';

interface Props {
  recentRoomCode?: string;
  onResumeRoom?: () => void;
  onCreateRoom: () => void;
  onJoinRoom: () => void;
}

export function HomeView({ onCreateRoom, onJoinRoom, recentRoomCode, onResumeRoom }: Props) {
  return (
    <div className="home-view">
      <h1 className="game-title">Gaia Project</h1>
      <p className="game-subtitle">{LOST_FLEET_DISPLAY_NAME} 에디션 · 4인</p>
      <div className="home-actions">
        {recentRoomCode && onResumeRoom && (
          <button className="btn btn-primary" onClick={onResumeRoom}>
            이어하기 · {recentRoomCode}
          </button>
        )}
        <button className="btn btn-primary" onClick={onCreateRoom}>
          방 만들기
        </button>
        <button className="btn btn-secondary" onClick={onJoinRoom}>
          방 참가하기
        </button>
      </div>
      <div className="home-replay-entry">
        <a className="btn btn-secondary" href="?aiReplay=1">AI 리플레이</a>
      </div>
    </div>
  );
}
