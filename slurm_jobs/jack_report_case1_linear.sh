#!/usr/bin/env bash
#SBATCH --job-name=jack_case1_linear
#SBATCH --output=jack_case1_linear_%j.out
#SBATCH --error=jack_case1_linear_%j.err
#SBATCH --account=chipilskigroup_q
#SBATCH --partition=chipilskigroup_q
#SBATCH --time=2-00:00:00
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

# SPEEDY forecasts are process-parallel. Keep each process and the numerical
# libraries single-threaded so the job stays within its Slurm CPU allocation.
export AMLCS_FORECAST_WORKERS="${SLURM_CPUS_PER_TASK:-1}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

python amlcs/workflows/jack_report/preflight.py
python amlcs/workflows/jack_report/run_cases.py \
    --case 1 --method both --execute --skip-preflight
# Jack's case-1 Table 7 value came from option_mask=2. The handoff uses the
# multivariate option_mask=1 LETKF and therefore treats its comparison as
# informational until the multivariate tuning sweep is complete.
python amlcs/workflows/jack_report/check_results.py \
    --case 1 --method ensf --strict
python amlcs/workflows/jack_report/check_results.py \
    --case 1 --method letkf
