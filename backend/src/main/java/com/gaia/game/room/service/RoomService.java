package com.gaia.game.room.service;

import com.gaia.game.room.dto.CreateRoomRequest;
import com.gaia.game.room.dto.RoomResponse;
import com.gaia.game.room.entity.Room;
import com.gaia.game.room.repository.RoomRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class RoomService {
    private final RoomRepository roomRepository;

    public RoomResponse create(CreateRoomRequest request) {
        return RoomResponse.from(roomRepository.save(new Room(request.title(), request.maxPlayers())));
    }

    public List<RoomResponse> findAll() {
        return roomRepository.findAll().stream()
                .map(RoomResponse::from)
                .toList();
    }

    public RoomResponse findById(Long roomId) {
        Room room = roomRepository.findById(roomId)
                .orElseThrow(() -> new IllegalArgumentException("방을 찾을 수 없습니다."));
        return RoomResponse.from(room);
    }

    public RoomResponse start(Long roomId) {
        Room room = roomRepository.findById(roomId)
                .orElseThrow(() -> new IllegalArgumentException("방을 찾을 수 없습니다."));
        room.start();
        return RoomResponse.from(room);
    }
}
