import { useState } from 'react';
import { HomeView } from './HomeView';
import { CreateRoomView } from './CreateRoomView';
import { JoinRoomView } from './JoinRoomView';
import { WaitingRoomView } from './WaitingRoomView';
import { FactionSelectView } from './FactionSelectView';
import { useRoomStore } from '../../store/roomStore';

type LobbyView = 'home' | 'create' | 'join' | 'waiting' | 'faction';

interface Props {
  onGameStart: () => void;
}

export function GameLobby({ onGameStart }: Props) {
  const roomCode = useRoomStore((s) => s.roomCode);

  // If we already have a roomCode (e.g. reconnect), skip to waiting
  const initialView: LobbyView = roomCode ? 'waiting' : 'home';
  const [currentView, setCurrentView] = useState<LobbyView>(initialView);

  function navigate(to: LobbyView) {
    setCurrentView(to);
  }

  switch (currentView) {
    case 'home':
      return (
        <HomeView
          onCreateRoom={() => navigate('create')}
          onJoinRoom={() => navigate('join')}
        />
      );
    case 'create':
      return (
        <CreateRoomView
          onRoomCreated={() => navigate('waiting')}
          onBack={() => navigate('home')}
        />
      );
    case 'join':
      return (
        <JoinRoomView
          onRoomJoined={() => navigate('waiting')}
          onBack={() => navigate('home')}
        />
      );
    case 'waiting':
      return (
        <WaitingRoomView
          onGameStart={onGameStart}
          onFactionSelect={() => navigate('faction')}
        />
      );
    case 'faction':
      return <FactionSelectView onGameStart={onGameStart} />;
    default:
      return null;
  }
}
