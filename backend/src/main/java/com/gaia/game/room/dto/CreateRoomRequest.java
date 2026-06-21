package com.gaia.game.room.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

public record CreateRoomRequest(
        @NotBlank String title,
        @Min(1) @Max(4) int maxPlayers
) {
}
