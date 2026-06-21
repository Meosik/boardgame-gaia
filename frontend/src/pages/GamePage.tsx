import { useParams } from 'react-router-dom';

export default function GamePage() {
  const { gameId } = useParams();

  return (
    <section>
      <h2>Game #{gameId}</h2>
      <p>게임 보드, 플레이어 패널, 액션 패널 구현 예정</p>
    </section>
  );
}
