import { useEffect, useState } from 'react';
import { HomeView } from './HomeView';
import { CreateRoomView } from './CreateRoomView';
import { JoinRoomView } from './JoinRoomView';
import { WaitingRoomView } from './WaitingRoomView';
import { FactionSelectView } from './FactionSelectView';
import { useRoomStore } from '../../store/roomStore';

import { readRecentRoom, rememberRoom } from '../../store/recentRoom';

type LobbyView = 'home' | 'create' | 'join' | 'waiting' | 'faction';

interface Props {
  onGameStart: () => void;
  manualControl?: boolean;
}

export function GameLobby({ onGameStart, manualControl = false }: Props) {
  const roomCode = useRoomStore((s) => s.roomCode);

  const [recentRoom] = useState(readRecentRoom);
  useEffect(() => {
    const saved = useRoomStore.getState();
    if (saved.roomCode && saved.playerId !== null && saved.sessionToken) {
      rememberRoom({ roomCode: saved.roomCode, playerId: saved.playerId, sessionToken: saved.sessionToken,
        nickname: saved.nickname, manualControl: manualControl || saved.manualControl });
    }
  }, [roomCode, manualControl]);

  // If we already have a roomCode (e.g. reconnect), skip to waiting
  const initialView: LobbyView = roomCode ? 'waiting' : recentRoom ? 'home' : manualControl ? 'create' : 'home';
  const [currentView, setCurrentView] = useState<LobbyView>(initialView);

  function navigate(to: LobbyView) {
    setCurrentView(to);
  }

  switch (currentView) {
    case 'home':
      return (
        <HomeView
          recentRoomCode={recentRoom?.roomCode}
          onResumeRoom={recentRoom ? () => {
            useRoomStore.getState().actions.resumeRoom(recentRoom);
            navigate('waiting');
          } : undefined}
          onCreateRoom={() => navigate('create')}
          onJoinRoom={() => navigate('join')}
        />
      );
    case 'create':
      return (
        <CreateRoomView
          manualControl={manualControl}
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
      return <FactionSelectView onGameStart={onGameStart} emphasizeStructures={manualControl} />;
    default:
      return null;
  }
}
