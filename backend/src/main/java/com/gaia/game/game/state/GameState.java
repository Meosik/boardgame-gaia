package com.gaia.game.game.state;

public record GameState(
        Long gameId,
        int round,
        Long currentPlayerId,
        String status
) {
}
