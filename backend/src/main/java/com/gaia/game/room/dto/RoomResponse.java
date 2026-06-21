package com.gaia.game.room.dto;

import com.gaia.game.room.entity.Room;
import com.gaia.game.room.entity.RoomStatus;

public record RoomResponse(
        Long id,
        String title,
        int maxPlayers,
        RoomStatus status
) {
    public static RoomResponse from(Room room) {
        return new RoomResponse(room.getId(), room.getTitle(), room.getMaxPlayers(), room.getStatus());
    }
}
