import { useCallback, useEffect, useRef, useState } from 'react';
import { GaiaWebSocket } from '../api/websocket';
import type { ClientCommand, ClientFrame, ServerMessage } from '../types/game';

interface UseWebSocketReturn {
  isConnected: boolean;
  send: (msg: ClientFrame) => void;
  sendCommand: (command: ClientCommand, expectedRevision: number) => string;
  lastMessage: ServerMessage | null;
}

export function useWebSocket(roomCode: string): UseWebSocketReturn {
  const clientRef = useRef<GaiaWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<ServerMessage | null>(null);

  useEffect(() => {
    const client = new GaiaWebSocket(roomCode);
    clientRef.current = client;

    const offState = client.onStateChange(setIsConnected);
    const offMsg = client.on(setLastMessage);

    client.connect();

    return () => {
      offState();
      offMsg();
      client.disconnect();
      clientRef.current = null;
    };
  }, [roomCode]);

  const send = useCallback((msg: ClientFrame): void => {
    clientRef.current?.send(msg);
  }, []);

  const sendCommand = useCallback((command: ClientCommand, expectedRevision: number): string => {
    return clientRef.current?.sendCommand(command, expectedRevision) ?? '';
  }, []);

  return { isConnected, send, sendCommand, lastMessage };
}
