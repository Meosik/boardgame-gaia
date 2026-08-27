import { useCallback, useEffect, useRef, useState } from 'react';
import { GaiaWebSocket } from '../api/websocket';
import type { ClientCommand, ClientFrame, ServerMessage } from '../types/game';

interface UseWebSocketReturn {
  isConnected: boolean;
  send: (msg: ClientFrame) => void;
  sendCommand: (command: ClientCommand, expectedRevision: number) => string;
  /**
   * Every message received since mount, in arrival order — append-only, a
   * new message is never dropped in favor of the next one. A single
   * "lastMessage" state slot (this hook's previous shape) silently loses
   * any message that isn't the last of a batch: the server can broadcast
   * several messages back-to-back (e.g. `handle_player_ready`'s `snapshot`
   * immediately followed by a `lobby_state`), and if both land within the
   * same React update batch, only the final `setState` call's value survives
   * — the earlier one, and the `useEffect` that would have reacted to it,
   * never fire. That's exactly how the room-full-and-ready-but-never-starts
   * bug reproduced: the `snapshot` carrying the real `GameState` (the only
   * signal that faction selection/bidding has started) lost the race against
   * the `lobby_state` broadcast sent right after it.
   */
  messages: ServerMessage[];
}

export function useWebSocket(roomCode: string): UseWebSocketReturn {
  const clientRef = useRef<GaiaWebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ServerMessage[]>([]);

  useEffect(() => {
    const client = new GaiaWebSocket(roomCode);
    clientRef.current = client;

    const offState = client.onStateChange(setIsConnected);
    const offMsg = client.on((msg) => setMessages((prev) => [...prev, msg]));

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

  return { isConnected, send, sendCommand, messages };
}
