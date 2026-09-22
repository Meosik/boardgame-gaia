#!/usr/bin/env bash
set -euo pipefail

# Reject login-node execution before even starting Python.
: "${SLURM_JOB_ID:?Enter a Slurm GPU allocation first}"
: "${SLURM_JOB_NODELIST:?Missing allocated compute nodes}"
node=$(hostname -s)
if ! scontrol show hostnames "$SLURM_JOB_NODELIST" | cut -d. -f1 | grep -Fxq -- "$node"; then
    echo 'Refusing Python on a host outside the Slurm allocation' >&2
    exit 1
fi
: "${CONDA_PREFIX:?Activate your private gaia Conda environment first}"
case "$(realpath "$CONDA_PREFIX")" in
    /data/"$USER"/*) ;;
    *) echo 'Use a private environment under /data/$USER, not a shared environment' >&2; exit 1 ;;
esac
test -x "$CONDA_PREFIX/bin/python"
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
# Keep Ray's nested Unix socket paths below Linux's 108-byte address limit.
# mktemp creates a private directory; a username in the path is unnecessary.
scratch=$(mktemp -d "/tmp/gaia-gpu.XXXXXXXX")
echo "Diagnostic output (on $node): $scratch/result"
# Leave CUDA_VISIBLE_DEVICES exactly as Slurm assigned it. cuda:0 is logical.
exec "$CONDA_PREFIX/bin/python" -B "$script_dir/gpu_smoke.py" --output "$scratch/result"
