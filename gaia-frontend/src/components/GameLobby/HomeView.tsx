interface Props {
  onCreateRoom: () => void;
  onJoinRoom: () => void;
}

export function HomeView({ onCreateRoom, onJoinRoom }: Props) {
  return (
    <div className="home-view">
      <h1 className="game-title">Gaia Project</h1>
      <p className="game-subtitle">Lost Fleet Edition — 4 Players</p>
      <div className="home-actions">
        <button className="btn btn-primary" onClick={onCreateRoom}>
          방 만들기
        </button>
        <button className="btn btn-secondary" onClick={onJoinRoom}>
          방 참가하기
        </button>
      </div>
    </div>
  );
}
