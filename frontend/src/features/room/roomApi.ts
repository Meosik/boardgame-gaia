import { apiClient } from '../../api/client';

export type Room = {
  id: number;
  title: string;
  maxPlayers: number;
  status: string;
};

export async function getRooms(): Promise<Room[]> {
  const response = await apiClient.get('/rooms');
  return response.data.data;
}

export async function createRoom(title: string, maxPlayers: number): Promise<Room> {
  const response = await apiClient.post('/rooms', { title, maxPlayers });
  return response.data.data;
}
