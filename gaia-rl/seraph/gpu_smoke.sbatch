#!/usr/bin/bash
#SBATCH --job-name=gaia-gpu-smoke
#SBATCH --partition=batch_ugrad_advisor_x
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-gpu=8
#SBATCH --mem-per-gpu=32G
#SBATCH --time=00:10:00
#SBATCH --output=logs/gaia-gpu-%j.out

set -euo pipefail
# Submit from the repository root after activating your private Conda environment.
cd -- "$SLURM_SUBMIT_DIR"
bash gaia-rl/seraph/gpu_smoke.sh
