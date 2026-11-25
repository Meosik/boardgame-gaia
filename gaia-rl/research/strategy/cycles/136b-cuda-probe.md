# Cycle 136b — CUDA 프로브(command, 판정 없음) — lab 서비스에서 CUDA가 안 보임

A/B 아님(`kind: command`, 팔 없음). 대상 부품: PPO 학습기의 `--learner-gpu`(2f6d494, 갱신만 CUDA GPU 1개)를 lab 기계에서
쓸 수 있는가. 출처 id 없음(인프라 확인). 큐: 2026-11-25 E331의 ⏩(코덱스 이상 없음, 사용자 「ppo 연산을 GPU가 하지 않는다고?」).
사전 등록: **판정 없음**(읽기 전용, 학습 · 대국 없음) — `cuda_available`이 true면 GPU 속도 팔(`--learner-gpu`, 러너 8) 제안,
false면 이 기계에서는 GPU 학습을 못 하고 Seraph · 사용자 PC 쪽(사용자 결정). 같이 볼 것: 장치 수 · 장치 이름 · VRAM ·
`CUDA_VISIBLE_DEVICES` · `nvidia-smi` 유무.
시드 · 대국 · 예산 없음. 실행 파이썬 `/home/sohegi/projects/gaia-work/gaia-rl/.venv/bin/python`(136a와 같은 것),
agentmaco, lab 커밋 d8b2e70, 2026-11-25 18:46:18 → 18:46:21(3초). 결과: `lab/results/136b-cuda-probe.md`.

**Health: 깨끗함.** 종료 코드 0, 지표 파일 기록됨. 대국 · 결정 없음. 검수 절 없음(command).

## Charges in rounds 1–3 (the verdict)

해당 없음 — 대국이 없는 command이고 사전 등록이 「판정 없음」이다.

## 지표 (`runs/lab-136b-cuda-probe/metrics.json`)

| 항목 | 값 |
|---|---|
| torch | 2.14.0+cu130 (CUDA 런타임 13.0으로 빌드된 휠) |
| `torch.cuda.is_available()` | **false** |
| 장치 수 | 0 |
| 장치 이름 · VRAM | 없음 |
| `CUDA_VISIBLE_DEVICES` | 미설정(환경 변수로 가린 것이 아님) |
| `nvidia-smi` | PATH에 없음 |

## Activation

프로브는 lab 서비스(systemd 사용자 서비스 `gaia-lab`) 안에서, 136a가 쓴 것과 같은 작업 트리 venv 파이썬으로 돌았다 —
PPO 학습이 실제로 도는 환경 그대로다. 봇 턴 환경의 값(`cuda_available` false, `nvidia-smi` 없음, E331)과 같다.

## Reading (HANDOFF 1 order — 판정이 없어 원인 구분만)

- **이 기계(agentmaco)의 lab 환경에는 쓸 수 있는 CUDA GPU가 없다.** torch는 CUDA 빌드라 휠 문제가 아니고,
  `CUDA_VISIBLE_DEVICES`도 미설정이라 가려진 것도 아니다. 장치 수 0은 PATH와 무관하다. 한계: 이 프로브는 「NVIDIA 하드웨어가
  없음」과 「드라이버가 없음」을 구분하지 않는다(`nvidia-smi`가 없다는 것까지만 확인).
- 따라서 `--learner-gpu`는 이 기계에서 거부된다(CPU 폴백 없음, 2f6d494). GPU 경로는 여전히 실행 검증이 안 됐다
  (`seraph/gpu_smoke.py`의 1회 갱신 확인만 있음).
- **GPU가 있어도 얻을 수 있는 몫의 추정(136a single 팔, 참고 — 136a는 끝난 실험이 아님)**: single 팔은 끝까지 돌았다
  (`runs/lab-136a-…/single/pilot.json`을 `tools/ppo_speed.py`의 `summarize`로 집계): 389반복 / 1802.6초, 49,792결정 =
  **시간당 99,438결정**, 반복 평균 4.63초, 타이머 평균 표집 3.73초 · 갱신 1.31초(합 5.04초로 반복 평균보다 큼 — RLlib 타이머 값
  그대로), 드라이버 RSS 최대 5,311 MiB, 끝난 판 수는 집계 안 됨(NaN). 갱신 비중 26–28%는 **추정**이다: 타이머 합(5.04초)이
  반복 평균(4.63초)보다 크고 `summarize`는 보고된 타이머를 단순 평균하므로 실제 소요 시간 비중으로 확정할 수 없다(토론 1/1 수용).
  지금 설정(배치 128 · minibatch 32 · 인코딩 4 · 한 프로세스)에서 GPU 몫은 **약 1.35–1.4배로 추정**되며,
  GPU 위치 판단의 확정 근거로 쓰지 않는다.
- **136a 「실패」의 실제 원인은 메모리 부족(전체 기계 OOM)** — 결과 페이지의 `already holds a run`은 그 뒤의 증상이다.
  `journalctl --user -u gaia-lab`과 커널 로그: 136a 첫 시작 18:05:11 → single 팔 완료 18:35 → parallel 팔(러너 8)이
  53반복(`parallel.log`)까지 간 18:39:46에 커널 전역 OOM(`constraint=CONSTRAINT_NONE`; 할당을 요청한 쪽은 도커의
  uptime-kuma, 죽은 것은 `ray::MultiAgent` 러너 1개 = anon 2.47 GB + shmem 2.06 GB) → `gaia-lab.service` `oom-kill`
  (서비스 메모리 최대 19.7 G, 스왑 최대 1.4 G) → 18:41:12 systemd 재시작 → lab이 136a를 처음부터 다시 실행 → `ppo_speed.py`의
  새 폴더 검사에 걸려 1초 만에 실패. 기계는 RAM 23.3 GB + 스왑 4 GB, 코어 16. `ppo_speed.py`의 메모리 표본
  (Pss · MemAvailable)은 프로세스가 같이 죽어 남지 않았다.
- parallel 팔의 속도는 읽을 수 없다: 53반복 / 약 4.7분(시작 시각은 single 폴더 수정 시각으로 추정, 러너 시작 시간 포함,
  타이머 없음) — single(4.63초/반복)보다 빠르다는 증거가 없다.
- **실서버와 같은 기계에서 전역 OOM이 났다.** 죽은 프로세스로 확인된 것은 Ray 러너뿐이지만(Ray 워커는
  `oom_score_adj` 1000), 실서버 컨테이너가 영향을 받았는지는 봇이 확인하지 못했다(도커 명령은 허용 목록 밖). 지금
  MemAvailable 20.0 GB, 스왑은 4.0 GB 중 2.9 GB가 아직 쓰이는 중.

코드 · 배포 변경 없음. lab 큐는 비어 있다(136 · 136a 실패, 136b 완료).

## Proposal (user decision, nothing queued)

- (ㄱ) **GPU 학습 위치**: 이 기계는 불가 → Seraph 또는 사용자 PC(사용자 결정). 단 GPU 몫은 약 1.4배로 추정될 뿐이라
  위치 판단의 확정 근거가 아니다 — 반복 안의 표집 · 갱신 시간을 실측한 뒤 정한다.
- (ㄴ) **병렬 표집 재측정(136c)**: `ppo_speed.py`에 메모리 하한 가드(MemAvailable이 하한 아래면 팔을 멈춤)와
  parallel 팔만 돌리는 선택을 넣고, 중단 때 프로세스 트리 전체를 정리해 남은 Ray 프로세스가 0인지 확인하며(지금은 부모만
  `kill()`, `tools/ppo_speed.py:135–138`), `training.py`가 `pilot.json`을 주기적으로 저장하게 한다(지금은 루프가 끝난 뒤 한 번,
  `python/gaia_rl/training.py:324`; `ppo_speed.py:149`는 종료 코드 0일 때만 읽음 — 토론 1/1 수용; 여러 파일이라 봇이 직접), 러너 수를 줄여 팔당 10분. **사용자가 정할 수치**: 러너 수
  (봇 권고 2와 4), 메모리 하한(봇 권고 8 GB). lab 약 25분.
- (ㄷ) **lab 재시작 안전**: 서비스가 죽었다 살아나면 돌던 실험을 처음부터 다시 돌린다 — 이번에는 새 폴더 검사가 막았지만
  없었으면 OOM이 반복됐을 것. 재시작 때 「돌던 중」 표시가 있으면 다시 돌리지 않고 `failed(중단)`으로 기록하게 고침(봇 턴).
- (ㄹ) 사용자 확인: 실서버(`shgaia.com`)가 18:39 이후 정상인지.
Bot recommendation: (ㄹ) 확인 → (ㄷ) → (ㄴ)(수치 확정 뒤) → (ㄱ)은 (ㄴ) 수치를 보고.
