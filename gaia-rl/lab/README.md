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
- Python 3.12 또는 3.13이 필요하다(엔진 바인딩 PyO3 0.23은 3.14 미지원). 배포판에 없으면 uv로 설치한다(sudo 불필요):
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

`review` — 두 번째 모델(OpenAI Codex CLI, `GAIA_LAB_REVIEW_MODEL` 기본 gpt-6-astra)의 코드 검수. 읽기 전용으로 돌고
답은 **요약 없이 원문 그대로** `results/<이름>.md`와 🔍 알림에 실린다(사용자 2026-10-21 "최소한 다른 agent의 검수").
```json
{"kind": "review", "note": "무엇을 검수하나",
 "commits": "abc1234..def5678", "paths": ["gaia-rl/tools/charge_rounds.py"],
 "prompt": "특히 볼 것", "timeout_minutes": 30}
```
`commits`(diff), `paths`(파일 전체), `result`(A/B 결과 이름: 그 판정을 반박) 가운데 있는 것을 쓴다. 검수자 답의 첫 줄은
`결론: 이상 없음` 또는 `결론: 지적 N건`. 자동으로 생기는 것 두 가지: ① `watch`가 pull에서 코드 파일(py·rs·ts·json 설정 등;
results·queue·seeds·docs 제외)이 바뀐 걸 보면 `review-code-<커밋>` 큐 파일을 만들어 커밋한다 ② **설계 검수(2026-10-22,
사용자 "실험에서 문제가 있다는건 실험을 시작하기 전에 이야기할 수 있어야지")**: `ab` 실험은 시작 전에 큐 파일(질문·사전 등록
판정·두 spec·표본·예산)을 Codex가 검수한다. `결론: 이상 없음`이면 바로 시작, 지적이 있으면 **보류** — 지적 원문은
`queue/<이름>.design.md`와 `🔍 # <이름> — 검수 (설계, 실험 보류)` 알림(봇이 대응 턴을 연다)에 실리고, 큐 파일에
`"design_review": {"findings": N, …}`가 적힌다. 설계를 고치거나 사용자가 정한 뒤 `"design_review": "accepted"`로 바꾸면
시작한다(`false`도 같음). 결과 뒤의 "## 검수" 절(판정 반박)은 **기본 꺼짐**(`"review": true`로만 켬). lab 기계에 codex가
없으면 코드 검수는 `failed` 결과로 남고 설계 검수는 경고 뒤 그대로 시작한다(`npm install -g @openai/codex` 뒤 `codex login`,
로그인은 사용자).

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

`lab/seeds.txt` 끝에 더 붙인다(4종족 고정 시드 생성). 예제는 `gaia-rl` 크레이트에 있다(`gaia-engine`이 아님).
두 번째 인자는 시작 번호가 아니라 **0부터 몇 번까지 훑을지**이므로, 이미 있는 시드는 빼고 새 것만 붙인다.
```sh
cd ~/projects/gaia-work/gaia-rl && cargo run --release --example faction_lineups -- geo-quartet 800000 Xenos,Taklons,Terrans,Geodens
```
cargo 없이(봇에서) 같은 일을 하려면 Python으로 번호 구간을 훑는다(2026-10-18, 731000–771000에서 22개):
```sh
cd ~/projects/gaia-work && gaia-rl/.venv/bin/python -c "import json,os,sys;os.environ['GAIA_ENGINE_FIXES_2']='1';sys.path[:0]=['gaia-rl/python'];from gaia_rl import Environment;want={'Xenos','Taklons','Terrans','Geodens'};hits=[]
for n in range(771000,811000):
    s='geo-quartet-%d'%n
    if {p['faction'] for p in json.loads(Environment(s,2000).snapshot_json())['state']['players']}==want: hits.append(s)
open('gaia-rl/lab/seeds.txt','a').write(''.join(h+'\n' for h in hits));print(len(hits))"
```

## 디스코드로 Claude에게 일 시키기 (호출식)

항상 떠 있는 것은 작은 봇(`lab/discord_claude.py`) 하나다. `#claude` 채널(또는 DM)에 쓴 **본인 메시지**마다
`~/projects/gaia-work`에서 `claude -p`를 한 번 실행하고 답을 올린다.

- 권한: `lab/claude-bot-settings.json`.
  - 읽기, 작업 폴더 수정, git, 읽기 전용 진단, 저장소 Python 실행만 허용한다.
  - 배포·재시작·삭제·비밀 파일 읽기는 거부한다.
  - 거부된 도구는 답 끝에 🔒로 표시되니, 필요하면 직접 실행한다.
- 명령: `!new` 새 대화, `!status` 상태(대화 턴 수 포함), `!stop` 실행 중단, `!q 질문` 싼 모델(Sonnet, `CLAUDE_QUICK_MODEL`)로 일회성 답(본 대화에 안 남음, 파일 수정 없음).
  한 번에 하나씩 처리하고, 나머지는 ⏳ 표시 후 순서대로 처리한다.
- RTK(2026-10-21, 사용자 설치 `cargo install --git https://github.com/rtk-ai/rtk` + `rtk init --global`): `~/.claude/settings.json`의
  PreToolUse 훅이 Bash 명령을 `rtk <명령>`으로 바꿔 출력을 압축한다. 봇 턴에도 적용되므로 허용 목록에 `Bash(rtk git log:*)`처럼
  **rtk 접두 항목을 기존 항목과 1:1로** 두었다(`Bash(rtk:*)` 전체 허용은 하지 않는다 — rm·sudo 우회가 되므로). `rtk bypass`는 읽기 명령만.
  새 명령을 허용할 때는 원형과 `rtk` 접두형을 함께 넣는다. 절약 통계: `rtk gain`.
- codegraph(2026-10-21, 사용자 설치 + `codegraph init`): 저장소 코드 그래프 CLI. 봇은 MCP 없이 CLI로 쓴다(`codegraph explore|query|node|files|callers|callees|impact|affected|status|sync` 허용,
  init·index·daemon·telemetry·upgrade는 사용자). 색인 `.codegraph/`(104MB)는 git 제외. 지시는 루트 `CLAUDE.md`와 봇 시스템 프롬프트에 있다.
- QMD(2026-10-21, 사용자 설치): 마크다운 로컬 검색기(BM25+벡터+재순위). codegraph가 못 보는 `research/`·`lab/` 문서를 색인한다.
  봇은 MCP 없이 CLI로 쓴다(`qmd query|search|vsearch|get|multi-get|ls|status|update|embed|collection list` 허용; 컬렉션 추가·삭제와
  `qmd mcp`는 사용자). 색인은 작업 트리 경로(`~/projects/gaia-work/gaia-rl/{research,lab}`) 기준이라 pull 뒤 `qmd update`로 갱신한다.
  만들기(사용자 한 번): `qmd collection add ~/projects/gaia-work/gaia-rl/research --name research`, 같은 식으로 `lab`, 그 뒤 `qmd update`, `qmd embed`.
  **봇 턴은 `qmd search`(BM25, 1초)만 쓴다**(2026-10-21 측정): `qmd query`(질의 확장 1.7B + 재순위 0.6B, CPU)는 2분을 넘겨 백그라운드로
  떨어지고 결과도 더 나빴다(네블라 6R 질문: query → STATUS.md 75%, search → 종족 트랙표·충돌표·HANDOFF 해당 줄). `qmd vsearch`도 확장 때문에
  1분 안팎. 번들 지침(`/usr/local/lib/node_modules/@tobilu/qmd/skills/qmd/SKILL.md`, `qmd skills get qmd --full`은 허용 목록 밖)에서 빌린 규칙:
  ① 스니펫은 단서일 뿐 — 적중의 `:줄` 앵커로 `qmd get "qmd://lab/x.md:120:40"`(또는 `qmd multi-get "#id1,#id2" -l 60`)을 읽은 뒤 답한다
  ② 확장 모델에 기대지 말고 `lex:`·`vec:`를 직접 쓴다 — 봇은 개행 명령이 거부되므로 한 줄만 가능: `qmd query "vec: <문서 말투의 풀어쓰기>" -n 5 --no-rerank`(7초, 임베딩 1회)가
  search 두 번 실패 뒤의 대안. `lex:` 한 줄 + 재순위(`-C 10`)는 21초인데 search와 같은 결과라 안 쓴다. 터미널에서 사람이 쓸 때는
  `qmd query $'intent: …\nlex: …\nvec: …'` 전체 형식이 가장 좋다(확장 모델 생략, 재순위만).
- 봇 턴은 MCP 서버를 싣지 않는다(`--strict-mcp-config --mcp-config lab/claude-bot-mcp.json`, 빈 설정; 계정의 Notion·Docs·Drive 커넥터는
  허용 목록 때문에 어차피 못 쓰면서 매 턴 도구 목록만 실렸음). 다시 켜려면 env `CLAUDE_BOT_MCP=1`.
- 프로젝트 스킬(2026-10-21, 사용자 "효과 있는 거 skill 만들어"): 절차를 `lab/skills/<이름>/SKILL.md`에 두고 `.claude/skills`로 연결해 쓴다
  (`lab-review` 결과 정리, `lab-queue` 큐 파일 작성, `explain` 수 하나 분석). 호출할 때만 본문이 실리므로 HANDOFF를 절차 때문에 읽지 않아도 된다.
  연결은 사용자 한 번(`.claude/`는 봇이 쓸 수 없음): `cd ~/projects/gaia-work && mkdir -p .claude && ln -s ../gaia-rl/lab/skills .claude/skills && git add .claude/skills && git commit -m "bot: link project skills" && git push origin HEAD:claude/epic-goodall-0ot55w`.
  스킬을 고칠 때는 `lab/skills/` 쪽 파일을 고친다(링크라 바로 반영).
- 토큰 절약(2026-10-21): 채널 대화는 `CLAUDE_SESSION_TURNS`(기본 10)턴이 되면 자동으로 끊고 다음 메시지부터 새 대화로 시작한다
  (이어진 대화는 호출마다 전체 맥락을 다시 보내므로). 새 대화의 맥락은 HANDOFF 5장에서 읽는다 — 주제가 끝나면 5장을 갱신해 둘 것.
- 설치 (agentmaco, 한 번):
  ```sh
  ~/.local/bin/uv venv --seed -p 3.12 ~/.venvs/gaia-claude-bot
  ~/.venvs/gaia-claude-bot/bin/pip install -q discord.py
  cd ~/projects/gaia-work && git pull --rebase origin claude/epic-goodall-0ot55w
  cp gaia-rl/lab/discord_claude.env.example gaia-rl/lab/discord_claude.env && chmod 600 gaia-rl/lab/discord_claude.env
  nano gaia-rl/lab/discord_claude.env          # 토큰, 내 사용자 ID, #claude 채널 ID
  cp gaia-rl/lab/discord-claude.service ~/.config/systemd/user/
  systemctl --user daemon-reload && systemctl --user enable --now discord-claude
  journalctl --user -u discord-claude -f       # "connected as ..." 이면 정상
  ```
- 자동 정리: `DISCORD_LAB_CHANNEL_ID`(모니터링 채널)를 설정하면, lab의 ✅ 결과 알림마다 봇이 `#claude`에서
  새 대화로 결과를 기록(사이클 문서, HANDOFF 갱신, 커밋·푸시)하고 다음 실험을 **제안만** 한다.
  큐에 넣을지는 그 대화에 답해서 정한다. 알림에서는 실험 이름만 읽는다.
- 두 번째 모델 검수(2026-10-21): lab의 🔍 검수 알림(코드 검수, `review` 종류)에 지적이 있으면 봇이 새 대화로 지적을 하나씩
  수정(커밋)하거나 반박한다. 반박이 있으면 답 첫 줄이 `불일치 — `로 시작하고 사용자가 정한다. `결론: 이상 없음`이면 턴을 열지 않는다.
  `!codex 질문`(`!gpt`)은 Codex(`CODEX_MODEL` 기본 gpt-6-astra)에게 직접 묻는 일회성 답(작업 트리 읽기 전용, Claude 대화와 무관).
  봇 기계에도 `codex`가 있어야 한다(`npm install -g @openai/codex`, `codex login`은 사용자). 설정은 호출마다 플래그로 주므로
  `~/.codex/config.toml`을 고칠 일은 없다.
- 대화 검수(2026-10-22, 사용자 "대화 중간중간에 codex가 개입"): 보통 턴이 끝날 때마다 봇이 사용자 메시지·Claude 답·그 턴의 커밋
  범위를 Codex에 보내고(읽기 전용, 턴 잠금 밖에서 `CODEX_WATCH_MINUTES` 기본 5분), 지적은 `🔍 코덱스 검수 지적`으로 그대로
  올라가며 다음 사용자 메시지 앞에 붙어 Claude에게 전달된다(사용자가 언급하면 수정·반박). `결론: 이상 없음`이면 한 줄만.
  `CODEX_WATCH=0`으로 끈다. `!q`·`!codex` 일회성 답은 검수하지 않는다.
- **Codex 별도 봇(2026-10-22, 사용자 "봇을 하나 새로 더 만드는 방식으로 가자")**: `lab/discord_codex.py`는 두 번째 디스코드 앱
  토큰(`CODEX_BOT_TOKEN`, 같은 env 파일)으로 뜨는 **읽기 전용** 봇이다. 같은 채널에서 `@Codex 질문`(또는 `!codex`/`!gpt`)에 최근
  대화 `CODEX_CONTEXT`(기본 12)개를 맥락으로 붙여 답하고, Claude 봇의 답이 `CODEX_WATCH_DELAY`(기본 20초) 멈추면 그 턴(사용자
  메시지·Claude 답·그 사이 커밋)을 검수해 `🔍 코덱스(…) 검수 지적`으로 올린다. 토큰이 설정되면 Claude 봇은 다른 봇을 멘션한
  메시지와 `!codex`를 건너뛰고(Codex 봇이 답함), 자기 안의 검수를 끄고, 채널에서 자기 마지막 답 뒤에 올라온 🔍 메시지를 다음
  사용자 메시지 앞에 붙인다. Claude가 긴 턴을 도는 동안에도 Codex는 답하고, Claude 봇 재시작(E77)에 검수가 죽지 않는다.
  두 봇이 서로의 글에 답하는 핑퐁은 없다: Codex 봇은 사용자 글에만 답하고 Claude 글은 검수만, Claude 봇은 사용자 글에만 답한다.
  설치(사용자 한 번): 디스코드 개발자 포털에서 두 번째 앱·봇 생성 → **Message Content Intent 켜기** → 서버에 초대(메시지 읽기·
  보내기·기록 보기) → 토큰을 `discord_claude.env`의 `CODEX_BOT_TOKEN`에 → `cp gaia-rl/lab/discord-codex.service ~/.config/systemd/user/`
  → `systemctl --user daemon-reload && systemctl --user enable --now discord-codex && systemctl --user restart discord-claude`
  (Claude 봇도 토큰을 읽어야 역할을 넘긴다) → `journalctl --user -u discord-codex -n 5`에 "connected as …; watch on".
  **토큰 한 파일(사용자 "토큰을 분리하지 않아도 괜찮나?")**: 두 봇은 같은 사용자·같은 기계라 파일을 나눠도 얻는 것이 없다. 중요한
  것은 모델 하위 프로세스가 토큰을 상속하지 않는 것 — `claude -p`·`codex exec`는 `clean_env()`(TOKEN·SECRET·WEBHOOK·API_KEY 이름 제거)
  로 뜬다. **지시·스킬 공유**: Codex는 저장소 루트 `AGENTS.md`(CLAUDE.md와 같은 내용을 Codex용으로)와 `.agents/skills`(→ `gaia-rl/lab/skills`,
  `.claude/skills`와 같은 폴더)를 읽는다. 스킬을 고치면 두 봇에 같이 반영된다.
- 같은 봇 토큰으로 채널 플러그인 세션(`claude --channels ...`)을 동시에 띄우지 않는다. 둘 다 답하게 된다.
