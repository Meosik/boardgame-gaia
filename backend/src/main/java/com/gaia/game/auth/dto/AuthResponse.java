package com.gaia.game.auth.dto;

public record AuthResponse(
        Long userId,
        String email,
        String nickname,
        String accessToken
) {
}
