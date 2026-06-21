package com.gaia.game.game.action;

import java.util.Map;

public record GameActionRequest(
        Long playerId,
        String actionType,
        Map<String, Object> payload
) {
}
