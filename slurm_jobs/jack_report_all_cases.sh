#!/usr/bin/env bash
#SBATCH --job-name=jack_all_cases
#SBATCH --output=jack_all_cases_%j.out
#SBATCH --error=jack_all_cases_%j.err
#SBATCH --account=chipilskigroup_q
#SBATCH --partition=chipilskigroup_q
#SBATCH --time=4-00:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=24G

set -euo pipefail

repo_root="${ENSF_SPEEDY_ROOT:-${SLURM_SUBMIT_DIR:-}}"
if [[ -z "$repo_root" || ! -f "$repo_root/start_da_session.sh" ]]; then
    echo "Submit this job from the EnSF_SPEEDY repository root." >&2
    exit 2
fi

cd "$repo_root"
source start_da_session.sh

export AMLCS_FORECAST_WORKERS="${SLURM_CPUS_PER_TASK:-1}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

python amlcs/workflows/jack_report/preflight.py
python amlcs/workflows/jack_report/run_cases.py \
    --case all --method both --execute --skip-preflight
# Jack's Table 7 used mixed LETKF block layouts, whereas the canonical handoff
# deliberately uses multivariate per-level blocks for every LETKF case. Keep
# EnSF reproduction strict, but report LETKF differences without failing the
# completed production job; the multivariate LETKF cases require fresh tuning.
python amlcs/workflows/jack_report/check_results.py \
    --case all --method ensf --strict
python amlcs/workflows/jack_report/check_results.py \
    --case all --method letkf
python amlcs/workflows/jack_report/plot_case1.py
