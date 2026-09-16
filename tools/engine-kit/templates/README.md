# Gaia Engine Kit — 개발용 전달본

Rust 게임 엔진과 Python 오프라인 4인 환경입니다. 자신의 컴퓨터에서 직접
봇을 구현·평가하는 용도이며, 웹사이트·게임 서버·DB·이미지·교사 정책·학습된
모델·PPO 실행기는 포함하지 않습니다. 전체 게임 규칙의 정확성이나 봇의 실력을
보증하는 정식 릴리스가 아닙니다.

## 배포 상태

**라이선스 및 공개 배포 조건은 미정입니다.** 이 문서는 사용/재배포 허가를
부여하는 라이선스가 아닙니다. 프로젝트 소유자와 이용 조건을 확인하세요.
원본의 룰북·게임 artwork·외부 공략 자료는 포함하지 않았습니다. 이를 제외했다고
상표·게임 자료·코드의 모든 배포 조건이 해결됐다는 뜻은 아닙니다.

`MANIFEST.json`은 생성 시 포함 파일의 SHA-256 목록이며 자기 자신은 제외합니다.
서명이나 보안 검증 완료 증명은 아닙니다. 작업 트리의 현재 파일을 복사하므로
Git 커밋과 반드시 같지 않습니다. 받은 파일과 설치한 엔진 버전을 함께 보관하세요.

## 구성

```text
gaia-engine/     Rust 규칙·상태·맵·점수 계산 및 규칙 데이터
gaia-rl/         오프라인 환경, Python 바인딩, 선택적 AEC/관측 인코더
examples/       학습 없이 합법 행동을 무작위 선택하는 예제
```

`gaia-engine`은 네트워크·DB에 의존하지 않습니다. Rust 프로젝트에서는
`gaia-engine = { path = "../gaia-engine" }` 형태의 로컬 의존성으로 사용할 수 있습니다.
PyO3 바인딩은 같은 엔진을 호출하므로 Python에서 규칙을 다시 구현하지 않습니다.

## 설치와 예제

필수: Python 3.12 이상, Rust 툴체인(`rust-toolchain.toml`), 해당 OS의 네이티브
빌드 도구. 첫 설치에는 패키지/크레이트 다운로드를 위한 인터넷이 필요합니다.
설치 이후 시뮬레이터는 외부 서버 없이 동작합니다. 아래는 Linux/macOS 셸 명령입니다.

```sh
# 이 README가 있는 전달본 루트에서 실행
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install ./gaia-rl
.venv/bin/python examples/random_bot.py --seed engine-kit-example
```

이 패키지는 원본과 같은 `gaia_rl` 이름을 사용하므로 반드시 별도 가상환경에
설치하세요. 기존 학습 환경 위에 덮어 설치하지 마세요. 플랫폼별 wheel은 제공하지
않으며, Windows 등 다른 플랫폼에서의 설치 검증 여부는 전달자에게 확인하세요.

예제가 성공하면 `complete: true`, 최종 점수, 행동 수, 엔진 빌드 ID가 출력됩니다.
봇은 약한 무작위 예제일 뿐입니다. 엔진 오류나 행동 수 제한은 실패로 종료되며
자동 패스·가짜 최종 점수로 바꾸지 않습니다.

## AI 연결 계약

```python
import json
from gaia_rl import Environment

env = Environment("my-seed", max_steps=10000)
snapshot = json.loads(env.snapshot_json())
player = snapshot["player"]
candidates = snapshot["candidates"]
index = 0  # 자신의 AI가 0 <= index < len(candidates) 중 선택
env.step(snapshot["decision_id"], index)
```

- `snapshot_json()`: 전체 상태, 현재 결정 주체, 합법 후보 목록, 결정 ID.
- `step(decision_id, candidate_index)`: 그 결정의 후보 하나 실행. 오래된 결정 ID와
  잘못된 인덱스는 거부됩니다. 후보 인덱스를 다음 상태에서 재사용하지 마세요.
- `fork(decision_id, candidate_index)`: 원본을 바꾸지 않고 해당 행동을 실행한
  독립 환경을 반환합니다. 검색 비용과 횟수는 호출자가 관리합니다.
- `is_terminal()` / `final_scores()`: 종료 여부와 최종 점수. 미종료 점수는 `None`.
- `reset(seed)`: 새 게임. 진행 중 게임의 복원 API가 아닙니다.
- 환경이 setup·자동 단계·반응 결정·턴 순서를 관리합니다. 좌석을 임의로 순환시키지 마세요.
- 현재 래퍼는 시드 기반 4인 세팅이며 종족 선택도 내부에서 처리합니다. 원하는 종족,
  커스텀 맵, 저장 상태 로드는 이 생성자의 지원 옵션이 아닙니다.
- `ENGINE_BUILD_ID`, `ENV_SCHEMA_VERSION`, 시드, 선택 기록을 결과에 남기세요.
  다른 규칙/인코딩 버전의 모델 호환성이나 기존 모델 이전을 보장하지 않습니다.
- 후보 목록의 모든 행동은 엔진 검증 대상이지만, 가능한 전략을 전부 열거한다는
  보장은 아닙니다. 현재 엔진은 복잡한 연방 검색이 `SearchLimit`에 도달하면
  경고를 기록하고 다른 합법 행동을 유지하며, 해당 결정의 연방 후보가 빠질 수 있습니다.
  원본의 이 동작을 전달본에서 변경하지 않았습니다.

## 선택적 강화학습 환경

PyTorch/RLlib는 제공하지 않습니다. 학습 알고리즘은 사용자가 선택합니다.
PettingZoo AEC 환경과 고정 길이 관측 인코더가 필요한 경우에만 설치합니다.

```sh
.venv/bin/python -m pip install './gaia-rl[aec]'
```

`gaia_rl.aec.GaiaAEC`와 `gaia_rl.encoding.FeatureEncoder`를 사용할 수 있습니다.
인코더의 후보/보드 용량을 넘거나 알 수 없는 행동을 만나면 오류를 냅니다.
합법 후보를 조용히 잘라내거나 패스로 대체하지 않습니다. 원시 JSON 환경과
인코더의 제약은 구분하세요. 다른 사람이 준 임의 모델/직렬화 파일을 실행하지 마세요.

## 검증

```sh
cargo test --locked --manifest-path gaia-rl/Cargo.toml
.venv/bin/python -m unittest discover -s gaia-rl/python/tests -p test_native.py -v
.venv/bin/python -m unittest discover -s gaia-rl/python/tests -p test_versions.py -v
# aec extra 설치 후:
.venv/bin/python -m unittest discover -s gaia-rl/python/tests -v
```

전달본에는 네이티브 환경 통합 테스트와 Python 환경 테스트를 포함합니다.
원본 엔진의 전체 통합 테스트, 프런트엔드/아트워크 대조 테스트는 이 전달본의
검증 범위가 아닙니다. 엔진 `src` 안의 원본 단위 테스트는 파일 무변경 보존을 위해
남아 있으므로 `cargo test --manifest-path gaia-engine/Cargo.toml` 전체 실행은
제외된 프런트엔드 자산 때문에 실패할 수 있습니다. 위 명령이 전달본의 검증 진입점입니다.

승점이나 경기 종료만으로 규칙 전수 검증 또는 AI 실력을 주장하지 마세요.
실력 비교에는 같은 규칙 버전, 공통 시드, 좌석/상대 조건, 별도 평가 맵이 필요합니다.
