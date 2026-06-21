import { useEffect, useState } from 'react';
import { createRoom, getRooms, Room } from '../features/room/roomApi';
import { Link } from 'react-router-dom';

export default function LobbyPage() {
  const [rooms, setRooms] = useState<Room[]>([]);

  async function loadRooms() {
    const data = await getRooms();
    setRooms(data);
  }

  async function handleCreateRoom() {
    await createRoom('테스트 방', 4);
    await loadRooms();
  }

  useEffect(() => {
    loadRooms();
  }, []);

  return (
    <section>
      <h2>Lobby</h2>
      <button onClick={handleCreateRoom}>방 생성</button>

      <ul>
        {rooms.map((room) => (
          <li key={room.id}>
            <Link to={`/rooms/${room.id}`}>
              {room.title} / {room.status} / {room.maxPlayers}명
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
