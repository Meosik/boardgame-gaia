# Services — 가이아 프로젝트 온라인

## 서비스 개요

서비스 레이어는 gaia-server 내에서 컴포넌트들을 조율하는 오케스트레이션 계층.

---

## Service 1: GameSetupService

**책임**: 게임 룸 생성부터 게임 시작 직전까지의 흐름 조율

**오케스트레이션 흐름:**
```
createRoom()
  → Randomizer.generate_setup(4)
  → RoomManager.create_room(host)
  → GameRepository.save_setup(room_code, setup)
  → 반환: RoomCode + GameSetup

regenerateSetup()
  → 호스트 권한 확인
  → Randomizer.new(new_seed).generate_setup(4)
  → RoomManager.update_setup(room_code, setup)
  → GameEventBus.broadcast(SetupUpdated { setup })

startGame()
  → 4명 참가 확인
  → 팩션 선택 완료 확인
  → GameState.new(setup, factions)
  → GameRepository.save_snapshot(state, round=0)
  → GameEventBus.broadcast(GameStarted { state })
  → RoomManager.update_room_state(InGame)
```

---

## Service 2: FactionSelectionService

**책임**: 팩션 선택 모드(자유 선택 / 비딩)별 흐름 조율

**자유 선택 흐름:**
```
selectFaction(player, faction_id)
  → 해당 쌍에서 유효한 팩션인지 확인
  → RoomManager.assign_faction(player, faction)
  → GameEventBus.broadcast(FactionSelected { player, faction })
  → 4명 완료 시 → GameSetupService.startGame()

requestLlmSuggestion(player, faction_pair)
  → gaia-ai POST /coach/faction-suggest { player_style, factions }
  → 응답을 해당 플레이어에게만 전송 (다른 플레이어 미노출)
```

**비딩 경매 흐름:**
```
startBidding()
  → BiddingEngine.new(players, faction_pairs)
  → GameEventBus.broadcast(BiddingStarted { state })

processBid(player, amount)
  → BiddingEngine.place_bid(state, player, amount)
  → GameEventBus.broadcast(BidPlaced { player, amount })
  → 낙찰 시 → GameEventBus.broadcast(BidWon { player, amount })
  →            플레이어에게 팩션+턴오더 선택 요청

processPass(player)
  → BiddingEngine.pass(state, player)
  → GameEventBus.broadcast(PlayerPassed { player })

selectAfterWin(player, faction, turn_order)
  → BiddingEngine.select_faction(state, player, faction, turn_order)
  → 다음 라운드 경매 시작 또는 모든 선택 완료 시 GameSetupService.startGame()
```

---

## Service 3: GameActionService

**책임**: 게임 액션 처리 및 상태 변이 조율

**흐름:**
```
processAction(player, action)
  → 현재 플레이어 턴 확인
  → RuleEngine.validate_action(state, action)
  → RuleEngine.apply_action(state, action) → events
  → GameRepository.save_event(room_code, each event)
  → ScoringEngine.calculate_round_score(state) (득점 변화 시)
  → GameEventBus.broadcast(ActionApplied { player, action, events, new_state_view })
  → TurnManagementService.advance_turn(state)
```

---

## Service 4: TurnManagementService

**책임**: 턴 순서 및 라운드 진행 관리

**흐름:**
```
advance_turn(state)
  → 다음 패스 안 한 플레이어로 턴 이동
  → 모든 플레이어 패스 시 → end_round()

end_round(state)
  → ScoringEngine.calculate_round_score(state) → round_scores
  → GameRepository.save_snapshot(state, round)  ← 라운드 종료 스냅샷
  → GameEventBus.broadcast(RoundEnded { round, scores })
  → round < 6 → start_next_round()
  → round == 6 → GameEndService.end_game()

start_next_round(state)
  → 라운드 번호 증가
  → 파워 수입 적용 (각 팩션)
  → GameEventBus.broadcast(RoundStarted { round })
```

---

## Service 5: GameEndService

**책임**: 게임 종료 및 최종 득점 처리

**흐름:**
```
end_game(state)
  → ScoringEngine.calculate_final_score(state) → FinalScoreBreakdown
  → ScoringEngine.apply_bid_penalties(scores, bid_results)
  → GameRepository.save_snapshot(state, round=7) ← 최종 스냅샷
  → GameRepository.save_final_scores(room_code, scores)
  → RoomManager.update_room_state(Ended)
  → GameEventBus.broadcast(GameEnded { final_scores, winner })
```

---

## Service 6: ReconnectService

**책임**: 플레이어 재접속 처리

**흐름:**
```
reconnect(player_token, room_code)
  → SessionManager.validate_session(player_token) → player_id
  → RoomManager.get_room(room_code) → room
  → GameRepository.reconstruct_state(room_code) → current_state
    (최신 스냅샷 + 이후 이벤트 재생)
  → 해당 플레이어에게 current_state 전송
  → 이후 실시간 이벤트 수신 재개
```

---

## Service 7: CoachingProxyService

**책임**: 프론트엔드와 gaia-ai 사이드카 사이의 프록시

**흐름:**
```
requestAnalysis(player_id, room_code)
  → GameRepository.load_latest_snapshot() → game_state
  → HTTP POST gaia-ai/coach/analyze { game_state, player_id }
  → 응답을 해당 플레이어에게만 전송 (WebSocket)

requestRulesAnswer(player_id, question, room_code)
  → HTTP POST gaia-ai/coach/rules { question, game_state }
  → 응답을 해당 플레이어에게만 전송

requestStrategy(player_id, room_code)
  → HTTP POST gaia-ai/coach/strategy { game_state, player_id }
  → 응답을 해당 플레이어에게만 전송
```
