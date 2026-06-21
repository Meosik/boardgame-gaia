package com.gaia.game.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;

public record SignupRequest(
        @Email String email,
        @NotBlank String nickname,
        @NotBlank String password
) {
}
