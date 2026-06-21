import { useParams } from 'react-router-dom';

export default function RoomPage() {
  const { roomId } = useParams();

  return (
    <section>
      <h2>Room #{roomId}</h2>
      <p>방 참가자, 준비 상태, 게임 시작 기능 구현 예정</p>
    </section>
  );
}
