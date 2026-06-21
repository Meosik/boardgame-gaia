package com.gaia.game.game.engine;

import com.gaia.game.game.action.GameActionRequest;
import com.gaia.game.game.state.GameState;
import org.springframework.stereotype.Component;

@Component
public class GameEngine {
    public GameState apply(Long gameId, GameActionRequest action) {
        // TODO: validate action and update game state.
        return new GameState(gameId, 1, action.playerId(), "IN_PROGRESS");
    }
}
