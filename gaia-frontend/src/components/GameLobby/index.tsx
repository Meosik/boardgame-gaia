import { useEffect, useState } from 'react';
import { LobbyHomeView } from './LobbyHomeView';
import { CreateRoomView } from './CreateRoomView';
import { WaitingRoomView } from './WaitingRoomView';
import { FactionSelectView } from './FactionSelectView';
import { useRoomStore } from '../../store/roomStore';

import { forgetRecentRoom, readRecentRoom, rememberRoom } from '../../store/recentRoom';

type LobbyView = 'lobby' | 'create' | 'waiting' | 'faction';

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

  // The room list is the front page: joining an existing game is the common case, and creating one
  // is a button on it. A reconnect still skips straight to the room the player already sits in, and
  // a saved room keeps its resume shortcut reachable even in the DEV flow that opens on creation.
  const initialView: LobbyView = roomCode
    ? 'waiting'
    : manualControl && !recentRoom
      ? 'create'
      : 'lobby';
  const [currentView, setCurrentView] = useState<LobbyView>(initialView);

  function navigate(to: LobbyView) {
    setCurrentView(to);
  }

  switch (currentView) {
    case 'lobby':
      return (
        <LobbyHomeView
          recentRoomCode={recentRoom?.roomCode}
          onResumeRoom={recentRoom ? () => {
            useRoomStore.getState().actions.resumeRoom(recentRoom);
            navigate('waiting');
          } : undefined}
          onTutorialStart={onGameStart}
          onCreateRoom={() => navigate('create')}
          onRoomJoined={() => navigate('waiting')}
        />
      );
    case 'create':
      return (
        <CreateRoomView
          manualControl={manualControl}
          onRoomCreated={() => navigate('waiting')}
          onBack={() => navigate('lobby')}
        />
      );
    case 'waiting':
      return (
        <WaitingRoomView
          onGameStart={onGameStart}
          onFactionSelect={() => navigate('faction')}
          onLeaveRoom={() => {
            // The seat is already freed server-side; drop the saved session too, or 이어하기
            // would offer to walk straight back into a room this player just left.
            const store = useRoomStore.getState();
            if (store.roomCode) forgetRecentRoom(store.roomCode);
            store.actions.reset();
            navigate('lobby');
          }}
        />
      );
    case 'faction':
      return <FactionSelectView onGameStart={onGameStart} emphasizeStructures={manualControl} />;
    default:
      return null;
  }
}
