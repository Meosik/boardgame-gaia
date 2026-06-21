package com.gaia.game.game.controller;

import com.gaia.game.game.action.GameActionRequest;
import com.gaia.game.game.engine.GameEngine;
import com.gaia.game.game.state.GameState;
import com.gaia.game.global.response.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;

@RestController
@RequestMapping("/api/games")
@RequiredArgsConstructor
public class GameController {
    private final GameEngine gameEngine;

    @GetMapping("/{gameId}")
    public ApiResponse<GameState> getState(@PathVariable Long gameId) {
        return ApiResponse.ok(new GameState(gameId, 1, 1L, "IN_PROGRESS"));
    }

    @PostMapping("/{gameId}/actions")
    public ApiResponse<GameState> submitAction(
            @PathVariable Long gameId,
            @RequestBody GameActionRequest request
    ) {
        return ApiResponse.ok(gameEngine.apply(gameId, request));
    }

    @GetMapping("/{gameId}/events")
    public SseEmitter events(@PathVariable Long gameId) throws IOException {
        SseEmitter emitter = new SseEmitter(60_000L);
        emitter.send(SseEmitter.event().name("CONNECTED").data("game-" + gameId));
        return emitter;
    }
}
