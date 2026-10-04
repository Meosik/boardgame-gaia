# lab — 실험 큐와 결과

실험을 git으로 주고받는다. 명령 복사나 결과 붙여넣기 없이, 큐 파일을 푸시하면 노트북이 돌리고 결과를 푸시한다.

```
lab/queue/<이름>.json     실험 정의 (Claude가 주로 추가)
lab/results/<이름>.md     사람이 읽는 결과 (표 + 결정 시간)
lab/results/<이름>.json   같은 결과의 데이터 (시드, 요약, 시간, 커밋, 기계)
lab/seeds.txt             아직 안 쓴 geo-quartet 시드. 쓴 시드는 결과·큐에서 자동으로 빠진다
```

결과 파일이 있는 실험은 다시 돌지 않는다. 다시 돌리려면 그 결과 두 파일을 지우고 푸시한다.
실패도 결과로 남는다(`status: failed`, 로그 끝부분 포함). 무한 재시도는 없다.

## 항상 켜진 기계(agentmaco)에 서비스로 등록

한 번만 하면 부팅 때 자동 시작, 죽으면 재시작, 실험은 가장 낮은 CPU 우선순위로 돈다(실서버 AI가 먼저).
실서버 체크아웃(`~/projects/gaia`)과 별도로 `~/projects/gaia-lab`에 받아서 쓴다.

```sh
curl -sO https://raw.githubusercontent.com/Meosik/boardgame-gaia/claude/epic-goodall-0ot55w/gaia-rl/lab/setup-host.sh \
  || git -C ~/projects/gaia show origin/claude/epic-goodall-0ot55w:gaia-rl/lab/setup-host.sh > setup-host.sh
bash setup-host.sh "$(git -C ~/projects/gaia remote get-url origin)"
```
- Python 3.12 이상이 필요하다. 배포판에 없으면 uv로 설치한다(sudo 불필요):
  `curl -LsSf https://astral.sh/uv/install.sh | sh` → `~/.local/bin/uv python install 3.12` →
  `GAIA_LAB_PYTHON="$(~/.local/bin/uv python find 3.12)" bash setup-host.sh ...`
- 엔진(Rust) 소스가 바뀐 코드를 받으면 lab이 알아서 다시 빌드한다.
- 동시 판 수와 웹후크는 `~/projects/gaia-lab/gaia-rl/lab/lab.env`.
- 상태 `systemctl --user status gaia-lab`, 로그 `journalctl --user -u gaia-lab -f`, 멈추기 `systemctl --user stop gaia-lab`.

## 노트북: 켜 두기

```sh
cd gaia-rl
git pull origin claude/epic-goodall-0ot55w
tmux new -s lab                                   # 창을 닫아도 계속 돌게
.venv/bin/python tools/lab.py watch --jobs 4      # 5분마다 pull → 대기 실험 실행 → 결과 push
# 빠져나오기: Ctrl+B 다음 D   /  다시 보기: tmux attach -t lab
```

- 노트북이 이 브랜치에 push할 수 있어야 한다(토큰 또는 SSH 키).
- 결과 파일 두 개만 커밋한다. 다른 로컬 변경은 건드리지 않는다.
- 시작·실패 알림을 디스코드로 받으려면 `export GAIA_LAB_WEBHOOK=<디스코드 웹후크 URL>` 후 실행한다.
  (채널 설정 → 연동 → 웹후크 → 새 웹후크 → URL 복사. URL은 비밀번호처럼 다루고 커밋하지 않는다.)
- 상태 보기: `.venv/bin/python tools/lab.py status`

## 실험 종류

`ab` — 교사 A/B (teacher_ab, 좌석 교대 2판씩)
```json
{"kind": "ab", "note": "무엇을 확인하나",
 "teacher_a": "tools/teacher-a-search2-h1-geodens-cap5.json",
 "teacher_b": "tools/teacher-a-search4-h1-geodens-cap20.json",
 "pairs": 12, "comparisons": 2}
```
`seeds`를 직접 주면 그 시드를 쓰고, 없으면 `seeds.txt`에서 `pairs`개를 새로 뽑는다.

`command` — 임의 명령 (gaia-rl/에서 실행). 앞으로 PPO 체크포인트 평가 같은 것을 여기에 넣는다.
```json
{"kind": "command", "note": "PPO 체크포인트 vs 교사",
 "run": ["{python}", "tools/some_eval.py", "--jobs", "{jobs}", "--out", "runs/x/metrics.json"],
 "metrics": "runs/x/metrics.json", "timeout_hours": 12}
```
`{python}`은 lab을 돌리는 파이썬, `{jobs}`는 `--jobs` 값으로 바뀐다.

`external` — 다른 곳(Seraph 등)에서 돈다. 노트북은 돌리지 않고 `status`에 "외부 실행 대기"로 보인다.

## Seraph PPO 결과 넣기 (실행은 직접)

Seraph 규칙(`seraph/README.md`)상 마스터 노드에서는 Python을 돌리지 않는다. 그래서 lab은 결과를 받는 통로만 제공한다.

1. (선택) 큐에 자리 표시: `lab/queue/ppo-001.json` → `{"kind": "external", "note": "PPO 첫 학습: ..."}`
2. 학습 스크립트가 끝에 지표 JSON을 `/data/$USER/...`에 남기게 한다. 예:
   `{"updates": 200, "env_steps": 1.2e6, "mean_return": 0.31, "win_rate_vs_teacher": 0.18, "checkpoint": "/data/$USER/ppo/ckpt-200"}`
3. 그 JSON(과 원하면 요약 md)을 노트북으로 가져와 기록한다.
   ```sh
   .venv/bin/python tools/lab.py record ppo-001 --metrics ppo-001.json --summary ppo-001.md --push
   ```
   결과가 다른 실험과 같은 자리에 쌓이고, Claude가 git으로 바로 읽는다.
4. (선택) 계산 노드에서 인터넷이 된다면 sbatch 스크립트에서 curl로 진행 알림을 보낼 수 있다.
   파이썬이 필요 없다.
   ```sh
   notify() { [ -n "${GAIA_LAB_WEBHOOK:-}" ] && curl -s -m 15 -H 'Content-Type: application/json' \
       -d "{\"content\": \"$1\"}" "$GAIA_LAB_WEBHOOK" >/dev/null || true; }
   notify "🧠 PPO $SLURM_JOB_ID 시작 ($(hostname))"
   ...
   notify "🧠 PPO $SLURM_JOB_ID 종료: exit $?"
   ```
   연결이 안 되면 조용히 넘어간다(학습은 멈추지 않는다).

PPO 정책이 교사처럼 수를 둘 수 있게 되면(정책을 불러오는 factory), 교사와의 대국 평가는 `ab` 또는 `command` 실험으로 노트북에서 돌린다.

## 시드가 모자랄 때

`lab/seeds.txt` 끝에 더 붙인다(4종족 고정 시드 생성).
```sh
cargo run --release --example faction_lineups -- geo-quartet 400000 Xenos,Taklons,Terrans,Geodens
```
