# KHU Seraph: moana GPU PPO 첫 확인

> **2026-09-17 실계정 확인:** 아래 최초 교재 기반 예시와 실제 등록이 다르다.
> 사용자 `shgkoihe`는 Account=`ugrad_ce`이며 `debug_ce_ugrad` 사용 권한을 확인했다.
> 이 파티션은 r/u/y를 모두 포함하므로 이번 무지도 학부생 확인은 `--nodelist=moana-u1`로 제한한다.
> u1(A2000)에서 기존 개인 환경의 CUDA 계산·역전파 성공, 엔진 빌드 및 pip check 성공을 사용자가 보고했다.
> r2에서는 시스템 Python도 cuInit=3, y7에서는 Prolog 실패가 발생했다. 두 오류의 근본 원인은 미확정이다.
> 현재 계정으로 아래 `debug_ugrad_advisor_x` 예시를 그대로 실행하지 않는다.
> 배치 파티션은 아직 실계정 검증 전이므로 `gpu_smoke.sbatch`도 아직 제출하지 않는다.

대상: **컴퓨터공학과 학부생 · 지도교수 없음**. 새 모델의 **PPO 1회 업데이트**만 확인한다.
PPO는 Python(RLlib/PyTorch), 게임 규칙·상태 전이는 Rust(PyO3)다.
웹 서버, shgaia.com, LIVE, 과거 대국/체크포인트를 변경하지 않는다.
이 문서와 스크립트는 준비물이며 **접속·설치·Slurm 제출을 자동 실행하지 않는다**.

## 1. 자료에서 확정한 규칙

제공된 `Seraph tutorial 1/3/4/5.pptx`(2023.09), `6.pdf`(2026.07)를 기준으로 했다.
충돌하면 최신 PDF를 우선한다. 원본 자료는 저작권 때문에 저장소에 복제하지 않는다.

| 항목 | 이번 설정 | 근거 |
|---|---|---|
| 대화형 파티션 | `debug_ugrad_advisor_x` | PDF p12–13 |
| 배치 파티션 | `batch_ugrad_advisor_x` | PDF p13,15 |
| 노드 | moana-u 계열, 특정 노드는 기본 고정하지 않음 | PDF p12 |
| 자원 | GPU 1, CPU 8, **시스템 RAM** 32GiB | PDF p12,15; VRAM 32GB라는 뜻 아님 |
| 마스터 | 접속·제출·가벼운 모니터링만 | PDF p5 |
| 계산 노드 | Python, 설치/빌드, 압축/해제, 학습 | PDF p6 |
| NAS `/data/$USER` | 코드·개인 Conda·완료 결과 보관 | PDF p3–4 |
| 실행 중 데이터/임시파일 | 노드 로컬 `/tmp` 또는 `/local_datasets` | PDF p3,6–7 |
| VS Code | Remote-SSH 허용, 큰 상위 폴더 탐색 금지 | PDF p8–9; 옛 PPT의 금지 안내 대체 |

마스터에서 Python/Conda 프로그램, `find`, `rg`, `grep -R`, AI 전체 저장소 스캔을 실행하지 않는다.
`/home`에 Conda를 설치하거나 공용 Conda에 `pip install`하지 않는다.
이 PPO는 이미지를 읽는 학습이 아니므로 별도 이미지 데이터셋이 필요하지 않다.
자료상 srun 최대 4시간, sbatch 최대 6일이지만 실제 계정 제한은 `show-assoc`/`show-qos`가 우선한다.
다른 파티션/계정으로 제한을 우회하지 않는다.

## 2. 접속 → 할당 확인 (아직 Python 실행 금지)

로컬 PC에서 **발급받은 moana 로그인 주소와 본인 ID**를 사용한다. 아래 대문자 값은 바꿔야 한다.
학교 내부는 포트 22, 외부는 30080(PDF p5, tutorial 3).

```bash
ssh -p 30080 YOUR_ID@YOUR_MOANA_LOGIN_HOST
```

마스터에서:

```bash
show-assoc
show-qos
slurm-gres-viz -i
squeue -u "$USER"

# 최초 환경 설치용 상한 제안 1시간. 환경 준비 후에는 아래 10분 예제 사용.
srun --partition=debug_ugrad_advisor_x --nodes=1 --ntasks=1 \
  --gres=gpu:1 --cpus-per-gpu=8 --mem-per-gpu=32G \
  --time=01:00:00 --pty bash
```

`-w moana-u2`는 자료의 예시일 뿐이므로 생략했다. 사용 가능한 노드를 Slurm이 배정한다.
파티션 권한 오류면 중단하고 관리자에게 계정 구분을 확인한다.

**할당된 계산 노드 셸 안에서만**:

```bash
hostname
echo "$SLURM_JOB_ID $SLURM_JOB_NODELIST"
scontrol show hostnames "$SLURM_JOB_NODELIST"
nvidia-smi
printf 'Slurm GPU mapping: %s\n' "${CUDA_VISIBLE_DEVICES-}"
findmnt -T /tmp
```

hostname이 할당 노드와 일치하고 `/tmp`가 노드 로컬인지 확인한다. 불명확하면 관리자 확인 후 진행한다.
`CUDA_VISIBLE_DEVICES`를 임의로 덮어쓰지 않는다. `cuda:0`은 할당받은 GPU의 논리 인덱스다.

## 3. 개인 Python 환경 및 소스 준비 (계산 노드)

이미 개인 Anaconda가 있으면 재설치하지 않는다. 없으면 tutorial 3 슬라이드 16–20대로
공식 Anaconda 배포 페이지에서 해당 Linux 아키텍처 설치 파일을 받고 체크섬을 확인한 뒤,
계산 노드에서 설치한다. 설치 경로는 **`/data/$USER/anaconda3`**다.
설치 파일 URL/버전을 임의로 고정하지 않고, 셸 설정 자동 변경 여부는 직접 선택한다.

```bash
# 설치 파일을 실제 다운로드한 경로로 바꿔서 실행 (기존 설치에 실행하지 않음)
# bash /data/$USER/downloads/Anaconda3-<VERSION>-Linux-x86_64.sh

source "/data/$USER/anaconda3/etc/profile.d/conda.sh"
export CONDA_PKGS_DIRS="/data/$USER/anaconda3/pkgs"
conda create --prefix "/data/$USER/anaconda3/envs/gaia-ppo" python=3.12 pip
conda activate "/data/$USER/anaconda3/envs/gaia-ppo"

export SETUP_SCRATCH
SETUP_SCRATCH=$(mktemp -d "/tmp/gaia-setup.${USER}.XXXXXXXX")
export TMPDIR="$SETUP_SCRATCH/tmp" PIP_CACHE_DIR="$SETUP_SCRATCH/pip"
export CARGO_TARGET_DIR="$SETUP_SCRATCH/target"
export CARGO_HOME="/data/$USER/.cargo" RUSTUP_HOME="/data/$USER/.rustup"
export PATH="$CARGO_HOME/bin:$PATH"
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$CARGO_TARGET_DIR"
```

소스는 **이 seraph 디렉터리가 포함된 작업본**을 `/data/$USER/repos/gaia`에 전달한다.
로컬 `.venv`, 빌드 `.so`, `target`, 과거 `runs`는 복사하지 않는다. Seraph에서 native를 다시 빌드한다.
기존 원격에 이번 파일이 아직 push되지 않았다면 clone만으로는 이 실행기가 생기지 않는다.
PPO-only 별도 저장소는 아직 만들지 않았고, 기존 `tools/engine-kit` 기본 출력은 PPO 의존성을 제외하므로 사용하지 않는다.

필요한 소스는 `gaia-rl`(python/src/seraph 및 Cargo·pyproject·build 파일),
`gaia-engine`(src/data/Cargo.toml), `rust-toolchain.toml`이다.
최소 패키지 검증 전에는 현재 저장소의 디렉터리 관계를 그대로 보존한다. 프런트엔드 실행은 필요 없다.

Rust는 저장소의 **1.95.0**을 사용한다. 없으면 공식 rustup 설치기를 검토해 위 개인 경로에 설치한다.
시스템 패키지/드라이버 설치나 `sudo`는 하지 않는다. 네트워크 차단·컴파일러/링커 부재는 관리자에게 확인한다.

```bash
cd "/data/$USER/repos/gaia"
rustup toolchain install 1.95.0 --profile minimal
rustc --version
python --version
```

## 4. CUDA PyTorch 선택 — nvidia-smi 확인 전에는 확정하지 않음

저장소 핀: **Python ≥3.12, Ray 2.58.0, Torch 2.14.0** (`../pyproject.toml`).
옛 공용 `pytorch1.12.1_p38` 환경은 사용하지 않는다.
GPU를 감지하면 pip가 알아서 적합한 CUDA 빌드를 고른다고 가정하지 않는다.
실제 GPU 모델·드라이버와 호환되는 CUDA wheel 인덱스를 명시한다.
PyTorch는 [공식 설치 선택기](https://pytorch.org/get-started/locally/)에서 CUDA 플랫폼을 선택하며,
드라이버 조건은 [NVIDIA 호환성 표](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)를 함께 확인한다.
**현재 Seraph 드라이버와 2.14.0 wheel 가용성은 미확인**이다.

아래 `TORCH_INDEX_URL`은 확인한 공식 CUDA 인덱스(형식 `https://download.pytorch.org/whl/cuXXX`)로 설정한다.
로컬 PC에서 cu130이 동작했다고 Seraph에도 cu130을 선택하면 안 된다.
핀 버전의 호환 wheel이 없으면 설치를 멈추고 의존성 변경을 별도 검토한다. 임의 다운그레이드/CPU 대체 금지.

```bash
# export TORCH_INDEX_URL='확인한 공식 CUDA wheel 인덱스'
: "${TORCH_INDEX_URL:?nvidia-smi와 공식 wheel 호환성을 먼저 확인하세요}"
python -m pip install 'torch==2.14.0' --index-url "$TORCH_INDEX_URL"
python -m pip install 'maturin>=1.15,<2.0'
cd "/data/$USER/repos/gaia/gaia-rl"
maturin develop --release --locked --extras train
python -m pip check
python - <<'PY'
import torch
print('torch:', torch.__version__, 'runtime:', torch.version.cuda)
print('available:', torch.cuda.is_available(), 'count:', torch.cuda.device_count())
assert torch.cuda.is_available() and torch.cuda.device_count() == 1
print(torch.cuda.get_device_name(0))
x = torch.ones(16, device='cuda', requires_grad=True)
x.square().sum().backward()
torch.cuda.synchronize()
assert torch.isfinite(x.grad).all()
print('CUDA forward/backward OK')
PY
```

`nvidia-smi`의 CUDA 표시는 드라이버 지원 수준이며 `torch.version.cuda`와 같은 값일 필요는 없다.
위 검증은 CUDA 커널 확인이지 PPO 검증은 아니다. 다음 단계를 별도로 실행한다.

## 5. 새 모델 PPO 한 번만 확인

설치용 할당이 아직 유효하면 그 안에서 바로 실행한다. 종료했다면 마스터에서 다시:

```bash
srun --partition=debug_ugrad_advisor_x --nodes=1 --ntasks=1 \
  --gres=gpu:1 --cpus-per-gpu=8 --mem-per-gpu=32G \
  --time=00:10:00 --pty bash
```

계산 노드에서 개인 환경 활성화 후:

```bash
source "/data/$USER/anaconda3/etc/profile.d/conda.sh"
conda activate "/data/$USER/anaconda3/envs/gaia-ppo"
cd "/data/$USER/repos/gaia"
bash gaia-rl/seraph/gpu_smoke.sh
```

실행기가 출력하는 `/tmp/gaia-gpu.<고유값>/result`가 결과 폴더다.
- GPU 없거나 여러 개가 보이면 실패한다. CPU 폴백 없음.
- Slurm 밖/마스터에서는 셸이 Python 시작 전에 거절한다. Python CLI도 할당 노드를 재확인한다.
- `num_learners=0`, `num_gpus_per_learner=1`: 로컬 learner 1개가 GPU를 사용한다.
  rollout은 CPU, 정책은 기존 shared-policy/width64, capacity2048/batch32/seed0, 업데이트 1회다.
- 기존 CPU `gaia_rl.training`/규칙/보상/종족 전략은 변경하지 않는다.
- Ray 로그·임시파일은 노드 로컬에 둔다. 해당 Python 프로세스 안에서만 HOME/TMPDIR를 격리한다.
- `complete.json`: 실제 learner CUDA 배치, 유한 loss, 가중치 변화, 정상 종료 확인 후에만 생성.
- `diagnostic-weights.pt`: 진단용 가중치만 저장. **optimizer/RNG 재개 체크포인트가 아니며 기존 resume에 넣지 않는다.**
- 오류 시 `failure.json`, 시간 제한/강제 종료 시 파일이 없을 수도 있다. `complete.json` 없으면 성공 아님.
- GPU 동작 확인은 학습 성능·승률·18종족 정책 완성·장기 학습 안정성 검증이 아니다.

할당 종료 전에 결과를 확인하고 작은 완료 산출물만 NAS로 한 번 보관한다. 실시간 대량 NAS 출력 금지.

```bash
# 실제 출력된 result 경로로 바꿀 것
RESULT=/tmp/gaia-gpu.UNIQUE/result
cat "$RESULT/complete.json"
test -f "$RESULT/complete.json" && (
  set -e
  DEST="/data/$USER/gaia-results/smoke-$SLURM_JOB_ID"
  mkdir -p "/data/$USER/gaia-results"
  mkdir "$DEST"  # 기존 결과가 있으면 중단
  cp "$RESULT/diagnostic-weights.pt" "$DEST/"
  cp "$RESULT/complete.json" "$DEST/"  # 완료 표시는 마지막
)
exit  # 할당 반환. 결과는 exit 전에 보관
```

## 6. 선택 사항: 같은 짧은 작업을 sbatch로 제출

먼저 debug 확인을 권장한다. `gpu_smoke.sbatch`는 **10분 상한, 1회 업데이트**이며 장기 학습 템플릿이 아니다.
제출 셸에 개인 환경의 `CONDA_PREFIX`가 있어야 한다. 이미 계산 노드에서 활성화한 셸에서 제출하거나,
마스터에서는 Conda/Python을 실행하지 않고 환경 경로만 export한다.

```bash
cd "/data/$USER/repos/gaia"
export CONDA_PREFIX="/data/$USER/anaconda3/envs/gaia-ppo"
mkdir -p logs  # sbatch가 로그를 열기 전에 존재해야 함
# 아래 명령은 실제 자원을 요청한다. 준비가 끝난 후 사용자가 직접 실행.
sbatch gaia-rl/seraph/gpu_smoke.sbatch
squeue -u "$USER"
# scancel JOB_ID  # 취소가 필요하면 본인의 해당 작업만
```

로그에 출력된 **계산 노드와 결과 경로**를 확인한다. batch 결과는 자동 NAS 복사하지 않으며
노드 로컬 파일은 임시이므로 회수가 필요하다. 회수용 계산 노드 접근도 Slurm/관리자 규칙을 따른다.
처음에는 결과 보관까지 같은 셸에서 할 수 있는 debug 경로가 더 간단하다.

VS Code 설정 제안(PDF p9; 사용자가 프로젝트 범위에서 적용):

```json
{
  "git.autofetch": false,
  "git.autofetchPeriod": 0,
  "git.enableSmartCommit": false,
  "git.suggestSmartCommit": false,
  "git.detectSubmodules": false
}
```

## 검증 범위

로컬 회귀: `gaia-rl/.venv/bin/python -B -m unittest discover -s gaia-rl/seraph -p 'test_*.py' -v`.
현재 PC의 RTX 3060 Laptop / Torch 2.14.0+cu130에서 새 모델 PPO 1회 업데이트를 실행해
CUDA learner·유한 loss·가중치 변화·완료 산출물을 확인했다. **Seraph에서 실행한 결과가 아니다.**
Seraph의 계정 권한, wheel 다운로드 가능 여부, GPU/드라이버, native 빌드, Slurm 실행은 아직 미검증이다.
