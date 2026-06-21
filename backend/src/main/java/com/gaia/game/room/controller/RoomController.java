package com.gaia.game.room.controller;

import com.gaia.game.global.response.ApiResponse;
import com.gaia.game.room.dto.CreateRoomRequest;
import com.gaia.game.room.dto.RoomResponse;
import com.gaia.game.room.service.RoomService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/rooms")
@RequiredArgsConstructor
public class RoomController {
    private final RoomService roomService;

    @PostMapping
    public ApiResponse<RoomResponse> create(@Valid @RequestBody CreateRoomRequest request) {
        return ApiResponse.ok(roomService.create(request));
    }

    @GetMapping
    public ApiResponse<List<RoomResponse>> findAll() {
        return ApiResponse.ok(roomService.findAll());
    }

    @GetMapping("/{roomId}")
    public ApiResponse<RoomResponse> findById(@PathVariable Long roomId) {
        return ApiResponse.ok(roomService.findById(roomId));
    }

    @PostMapping("/{roomId}/start")
    public ApiResponse<RoomResponse> start(@PathVariable Long roomId) {
        return ApiResponse.ok(roomService.start(roomId));
    }
}
