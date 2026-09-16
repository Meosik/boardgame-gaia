# AI 실행 + 이미지 관전

기존 게임판·행성·건물·기술/연방 타일 이미지를 사용하는 **읽기 전용 관전 UI**입니다.
온라인 게임 서버·DB·홈페이지 비밀번호가 필요하지 않습니다. 실행되는 AI는
무작위 합법 행동 예제이며, 강한 교사나 학습된 모델이 아닙니다. 학습을 자동 시작하지 않습니다.

## 최초 설치 (Linux/macOS)

Python 3.12+, Rust(`rust-toolchain.toml`), Node.js 20+ 및 npm과 네이티브 빌드 도구가 필요합니다.
처음에는 의존성 다운로드와 컴파일 때문에 시간이 걸립니다. 인터넷은 설치할 때 필요합니다.

```sh
python3 -m venv .venv
.venv/bin/python setup_viewer.py
```

Windows에서는 `py -3.12 -m venv .venv`, `.venv\Scripts\python.exe setup_viewer.py`를
사용할 수 있으나 이 전달본은 Linux에서만 실제 검증했습니다. 다른 프로젝트의 Python
환경 위에 설치하지 마세요. 기존 패키지 버전을 사용하며 취약점 전수 감사 완료를 뜻하지 않습니다.

검증 당시 개발 의존성에서 npm audit 경고 10개(치명적 1개 포함)가 남았습니다.
`npm audit --omit=dev`는 0개였으나 안전을 보증하지 않습니다. 의존성 버전을 임의로
올리지 않았고, 관전 서버는 로컬에서만 실행합니다.

## AI 경기 실행·관전

```sh
.venv/bin/python examples/watch_game.py
```

브라우저가 열리며 `http://127.0.0.1:8765/`에서 새 경기의 기록을 볼 수 있습니다.
브라우저가 열리지 않으면 주소를 직접 입력하세요. 바인딩은 로컬 전용이고 소스·비밀 파일은
제공하지 않습니다. 정적 화면과 그 실행에서 생성한 기보만 제공합니다.

- 예제 봇은 빨라서 화면을 열 때 이미 끝났을 수 있습니다. 하단 진행 막대를 처음으로
  옮기고 재생하면 한 수씩 볼 수 있습니다. 인위적인 생각 시간은 추가하지 않았습니다.
- 느린 자신의 AI로 교체하면 실행 중 LIVE로 새 행동을 따라갑니다. 정지·탐색·LIVE 기능은 기존 UI와 같습니다.
- 종료 후에도 관전 서버는 유지됩니다. 터미널에서 Ctrl+C로 종료합니다.
- 기존 LIVE 경기 목록의 점수는 게임 중 VP입니다. 정산을 포함한 최종 점수는
  실행 결과와 `runs/watch-*/result.json`의 `scores`를 확인하세요.
- 창을 닫는 것만으로 프로세스가 끝나지는 않습니다. 노트북 절전 중 실행은 멈추며,
  중간 게임 재개 기능은 없습니다. 기록은 `runs/watch-*/`에 남습니다.
- 다른 맵: `--seed my-game`. 다른 포트: `--port 8766`. 브라우저 자동 실행 제외: `--no-browser`.
- 화면 없이 기보 생성만: `--generate-only`. 오류나 행동 수 제한은 실패로 기록되며 가짜 완료/자동 패스로 바꾸지 않습니다.

## 자신의 AI 연결

`examples/watch_game.py`의 `choose(snapshot, rng)`를 바꾸면 됩니다.
현재 상태의 `snapshot['candidates']` 중 인덱스를 반환하세요. 현재 예제는 네 좌석 모두
같은 선택 함수를 사용하며, `snapshot['player']`로 좌석별 정책을 나눌 수 있습니다.
상대방 모델 업로드/임의 코드 실행 서비스나 홈페이지에서의 학습 기능은 포함하지 않습니다.

## 테스트

```sh
# 최초 설치 후, 저장소 루트
GAIA_REPLAY_INCOME_BIN="$PWD/gaia-rl/target/release/examples/replay_income" \
  .venv/bin/python -m unittest discover -s examples -p 'test_*.py' -v
GAIA_REPLAY_INCOME_BIN="$PWD/gaia-rl/target/release/examples/replay_income" \
  .venv/bin/python -m unittest discover -s gaia-rl/tools -p 'test_*.py' -v
cd gaia-frontend
npm test
npm run build
```

이미지 이용 조건은 [ASSET-NOTICE.md](ASSET-NOTICE.md)를 확인하세요. 비공개 초대를 통한
개발용 전달 요청으로 포함했으며, 재배포 허가를 확인했거나 새 라이선스를 부여한 것은 아닙니다.
미사용 원본 스캔·룰북 PDF·개인 기보·모델은 포함하지 않습니다. 게임/학습 규칙은 변경하지 않았습니다.
