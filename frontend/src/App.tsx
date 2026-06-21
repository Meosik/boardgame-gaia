import { Link, Route, Routes } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import LobbyPage from './pages/LobbyPage';
import RoomPage from './pages/RoomPage';
import GamePage from './pages/GamePage';

export default function App() {
  return (
    <div className="app">
      <header>
        <h1>Gaia Project Web</h1>
        <nav>
          <Link to="/">Lobby</Link>
          <Link to="/login">Login</Link>
        </nav>
      </header>

      <main>
        <Routes>
          <Route path="/" element={<LobbyPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/rooms/:roomId" element={<RoomPage />} />
          <Route path="/games/:gameId" element={<GamePage />} />
        </Routes>
      </main>
    </div>
  );
}
