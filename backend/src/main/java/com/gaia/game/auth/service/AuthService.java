package com.gaia.game.auth.service;

import com.gaia.game.auth.dto.AuthResponse;
import com.gaia.game.auth.dto.LoginRequest;
import com.gaia.game.auth.dto.SignupRequest;
import com.gaia.game.user.entity.User;
import com.gaia.game.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthService {
    private final UserRepository userRepository;

    public AuthResponse signup(SignupRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new IllegalArgumentException("이미 사용 중인 이메일입니다.");
        }

        User user = userRepository.save(
                new User(request.email(), request.nickname(), request.password())
        );

        return new AuthResponse(user.getId(), user.getEmail(), user.getNickname(), "temporary-token");
    }

    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.email())
                .orElseThrow(() -> new IllegalArgumentException("존재하지 않는 사용자입니다."));

        if (!user.getPassword().equals(request.password())) {
            throw new IllegalArgumentException("비밀번호가 일치하지 않습니다.");
        }

        return new AuthResponse(user.getId(), user.getEmail(), user.getNickname(), "temporary-token");
    }
}
