# Astra 구현 / Sol 검증 기반

- `../scripts/handoff_loop.sh --background`: nohup 시작. 요약은 기존
  `gaia-rl/research/strategy/STATUS.md`의 Handoff 구역에만 갱신한다.
- `QUEUE.md`의 승인 과제를 작성한 뒤 `next: astra`로 시작한다.
  `next: human`은 대기/실행 중단 요청이다. 초기 상태는 human이다.
- Astra=`codex exec --model gpt-6-astra`, Sol=`codex exec --model gpt-6-sol`.
  설치된 Codex 0.155.1의 `exec --help` 및 로컬 모델 목록에서 확인했다.
  프롬프트는 이 디렉터리의 `ASTRA_PROMPT.md` / `SOL_PROMPT.md`를 stdin으로 전달.
  인증은 기존 CLI 설정을 사용한다. 권한/샌드박스 우회 옵션은 사용하지 않는다.
- 2026-09-24 사용자 승인: **Sol에만** workspace-write와 네트워크 프록시를 함께
  적용하고 정확히 `127.0.0.1` 목적지만 허용한다. 외부 목적지 허용 규칙은 없으며
  광범위 사설망 허용과 상위 프록시 연결도 끈다. Astra의 네트워크 차단은 유지한다.
  네트워크만 단독으로 켜거나 프록시 실패 시 직접 접속으로 전환하지 않는다.
  전역 Codex/AppArmor 설정은 변경하지 않는다.
  이 제한은 Sol이 실행하는 명령·테스트에 적용되며 CLI 자체의 모델 API 연결과는 별개다.
  `python3 scripts/check_handoff_sandbox.py`로 실제 로컬 HTTP, 외부/사설망 직접
  접속 차단, 프록시 외부 목적지 차단, 작업 폴더 밖 쓰기 차단을 재검증할 수 있다.
  Codex 0.155.1에서 검증했으며 CLI/정책 변경 후에는 재검증이 필요하다.
  근거: https://learn.chatgpt.com/docs/agent-approvals-security#network-isolation
- 10초 polling. 안전하게 **CLI 호출 1회=사이클 1회**, 성공/실패 모두 집계한다.
  최대 6회 또는 대기 시간을 포함해 시작 후 8시간이면 next=human 후 종료한다.
  호출 중에도 시간 한도를 감시하여 CLI와 하위 프로세스를 종료한다.
- 각 호출 stdout/stderr, 구조화된 최종 결과, 시작 시 QUEUE 사본은
  `logs/<UTC timestamp>-<cycle>-<role>.*`. 기존 로그를 덮어쓰지 않는다.
- 결과 스키마 `status=gate_failed` 또는 CLI 비정상 종료/결과 누락은 실패다.
  첫 실패는 상대 역할로 인계(특히 Sol 실패 → Astra 수정), 연속 2회면 human.
  pass는 연속 실패를 초기화한다. human은 즉시 사람에게 인계한다.
- 프로세스 중복 실행은 flock으로 거부한다. 재시작에도 횟수·기한은 보존하며,
  중단된 호출이 있으면 자동 재실행하지 않고 human으로 보낸다.
  새 6회/8시간 세션은 정지 확인 후 `.loop-state.json`을 별도 이름으로 보관하고 시작한다.
- 실행 중 사람이 QUEUE를 수정하면 덮어쓰지 않는다. 외부 편집과 원자적 교체의
  아주 짧은 경합을 피하려면 `next: human`으로 멈춘 뒤 과제를 수정한다.
- `HANDOFF_CODEX`로 실행 파일 경로를 지정할 수 있다(쉘 문자열 실행 아님).
  `--max-cycles`, `--max-seconds`, `--poll-seconds`는 테스트/한도 축소용이다.
- 자동화가 새로운 튜닝 승인이나 설계 재량을 부여하지 않는다. 동결 A 소스 유지,
  기준 엔진 ON, 보류 실험 재측정 최소 12시드. 재측정 자체는 별도 승인 필요.
