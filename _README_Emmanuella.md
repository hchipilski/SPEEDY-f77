# Emmanuella handoff: continuing Jack's four DA experiments

This guide starts from a fresh GitHub fork and runs the audited continuation of
the four experiments in `Jacks_defense_report.pdf`. Do not reuse the older
`case1` through `case4` runner files from commit `0a2f8fe`; the corrected,
canonical runners are under `amlcs/workflows/jack_report/cases/`.

The workflow runs the selected EnSF configuration and a consistently
multivariate LETKF configuration for each case with the same 80-member initial
ensemble, synthetic truth, NoDA trajectory, 30 assimilation cycles, two-day
forecast interval, and full horizontal observation coverage used in the
report. The LETKF localization and inflation values from the report are useful
starting points, but they are not yet established as optimal for the uniformly
multivariate implementation used here.

## Source provenance

This reconstruction is based on Jack's source snapshot
`2f5b35c4716ba86aea65c5479dc5879c9aba2e98` (13 June 2026). Jack's
`testing-jack` branch subsequently advanced by 15 commits to
`0c8b6ae4aca633005da82d1fcbc83ca6c8a7aa4d` (20 July 2026), the branch head
that was handed off at
<https://github.com/jjs21b/SPEEDY-f77/tree/testing-jack> when this audit was
performed.

The later commits mainly add tuning summaries, validation utilities, selected
parameters, and plotting products. The DA-core files `amlcs/amlcs_da.py`,
`amlcs/observation.py`, and `amlcs/sequential_methods.py` are byte-for-byte
identical at the two Jack commits. An audit of the configurations whose RMSE
values match Table 7 found that Jack's production runs used mixed LETKF block
layouts: cases 1 and 4 used separate variable-level blocks (`option_mask=2`),
while cases 2 and 3 used multivariate per-level blocks (`option_mask=1`). This
conflicts with applying the report's more robust cross-variable LETKF rationale
consistently to all four experiments.

The corrected repository therefore adds workflow and metadata handling around
the DA core, restores the required observation options where Emmanuella's
attempted integration had replaced the driver, and deliberately uses
`option_mask=1` for every LETKF case. Use the corrected handoff revision below
for new experiments; use the two Jack hashes to document the upstream
scientific provenance and the archived Table 7 calculation.

## 1. Fork and clone the corrected repository

The handoff was developed on `debug_ella`, but that branch is now historical.
Do **not** use `debug_ella` as the starting point for new experiments. The
finalized handoff, including the multivariate LETKF configurations and tuning
cautions in this guide, is on `main`.

1. Open <https://github.com/hchipilski/SPEEDY-f77> in GitHub.
2. Select **Fork**, choose your GitHub account, and create the fork.
3. Clone your fork on the RCC filesystem. Replace `<github-user>` below with
   your GitHub username:

```bash
git clone git@github.com:<github-user>/SPEEDY-f77.git
cd SPEEDY-f77
git remote add upstream git@github.com:hchipilski/SPEEDY-f77.git
git remote -v
```

After cloning, create Emmanuella's working branch from the corrected upstream
`main` branch. This explicitly checks out the finalized handoff even if her
fork's default branch points somewhere else:

```bash
git fetch upstream main
git switch --create emmanuella/letkf-tuning upstream/main
git log -1 --oneline
```

Record the printed commit in every experiment log or report. If a final
handoff tag is provided later, create the working branch from that tag instead.

Keep `upstream` pointed at the source repository and `origin` pointed at your
fork. Make changes only on your own branch, then use a pull request to propose
changes upstream.

## 2. Create and activate the AMLCS environment

Initialize Conda using whichever installation exists on your RCC account:

```bash
if [[ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]]; then
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
else
    source /gpfs/research/software/python/anaconda311/etc/profile.d/conda.sh
fi
```

For a new environment:

```bash
conda env create --file environment/conda/environment.yml
conda activate amlcs
./environment/install-conda-hooks.sh
conda deactivate
conda activate amlcs
```

If an `amlcs` environment already exists, update it instead:

```bash
conda env update --name amlcs \
    --file environment/conda/environment.yml --prune
conda activate amlcs
./environment/install-conda-hooks.sh
conda deactivate
conda activate amlcs
```

Validate the complete Python, compiler, and NetCDF setup:

```bash
./environment/validate-environment.sh
```

For later login sessions in which Conda is already initialized, activate the
configured environment normally:

```bash
conda activate amlcs
```

`source start_da_session.sh` is an optional convenience for a shell where the
`conda` function is not yet available. It initializes Conda when necessary and
then runs `conda activate amlcs`. The Slurm scripts use it so batch shells do
not depend on a user's interactive-shell initialization.

Do not use the former `speedy_da_env` environment or paths under another
user's home directory.

## 3. Validate all inputs and configurations

Run the preflight before submitting any expensive job:

```bash
python amlcs/workflows/jack_report/preflight.py
```

It checks:

- all eight canonical EnSF/LETKF runner files;
- the alternative case-2 paper-specification runner;
- 80 initial ensemble members and restart files;
- all 30 required truth snapshots;
- the SPEEDY executable;
- observation operators, masks, inflation, and localization settings;
- distinct output directories for every case and method.

Preview the eight commands without executing them:

```bash
python amlcs/workflows/jack_report/run_cases.py \
    --case all --method both
```

The preview must list two commands for each of the four cases and end with
`Dry run only`.

## 4. Confirm the four experiment definitions

| Case | Observation system | EnSF selection | Initial LETKF tuning | LETKF layout |
| --- | --- | --- | --- | --- |
| 1: all linear | Direct UG1, VG1, TG1, TRG1, PSG1 | inflation 1.00 | radius 3, inflation 1.00 | multivariate per level |
| 2: all arctangent | Arctangent of all five fields | inflation 1.00 | radius 3, inflation 1.00 | multivariate per level |
| 3: WDG/WSG/TPH | WDG1 and WSG1; direct TG1, TRG1, PSG1 | inflation 1.00 | radius 2, inflation 1.15 | multivariate per level |
| 4: pressure only | Direct PSG1 only | inflation 1.00 | radius 2, inflation 1.30 | multivariate per level |

EnSF's `r=1` value is only a required folder-name placeholder; the original
EnSF analysis does not use LETKF localization. Observation spacing `s=1`
means every eligible horizontal grid point is observed.

For LETKF, `option_mask=1` groups all state variables defined at a given model
level into the same local analysis block. Observations within the local box can
therefore update every variable in that level through ensemble-estimated
cross-covariances. All four canonical LETKF runners, including the three
remaining cases 2--4, must retain `option_mask=1`. The preflight enforces this.

The radius and inflation entries above reproduce the values selected for the
report, not a completed tuning result for this unified multivariate layout.
Changing cases 1 and 4 from Jack's production `option_mask=2` changes the
analysis and can change the best radius and inflation. Before interpreting the
LETKF comparison as final, rerun the full tuning grid for each multivariate
case:

```text
radius    = 1, 2, 3, 4
inflation = 1.00, 1.15, 1.30, 1.45, 1.60
```

Keep tuning outputs separate from the canonical case directories until a new
setting has been selected and documented. Do not replace a canonical runner
based on a partial sweep.

## 5. Submit all four cases on Slurm

Run from the repository root with the `amlcs` environment active:

```bash
sbatch slurm_jobs/jack_report_all_cases.sh
```

This submits one allocation that runs the eight DA jobs sequentially in this
order:

```text
case 1 EnSF  -> case 1 LETKF
case 2 EnSF  -> case 2 LETKF
case 3 EnSF  -> case 3 LETKF
case 4 EnSF  -> case 4 LETKF
```

Sequential execution is intentional. The legacy AMLCS/SPEEDY driver creates
temporary build files in its working directory, so methods must not be launched
concurrently from the same checkout.

The batch request is:

- account and partition: `chipilskigroup_q`;
- one node and one Slurm task;
- 16 CPUs for that task;
- 24 GB memory;
- four-day wall time;
- 16 local multiprocessing forecast workers, one thread per worker.

The Slurm log is written to `jack_all_cases_<jobid>.out` and errors to
`jack_all_cases_<jobid>.err` in the directory from which `sbatch` was run.
The Python driver writes detailed per-run logs under `logs/`.

Do not run the expensive `--execute` command on a login node. If the all-cases
job is interrupted, inspect completed outputs before rerunning; do not mix a
new run with a partially completed output directory.

## 6. Output locations

The canonical output roots are:

```text
runs/jack_report/case1_linear/
runs/jack_report/case2_arctan/
runs/jack_report/case3_wind_tph/
runs/jack_report/case4_pressure_only/
```

Each method gets a parameter-encoded subdirectory. Important contents include:

- `runner.csv`: exact submitted configuration;
- `run_metadata.json`: input hash, Git commit, and resolved settings;
- `unified_cycle0.nc` through `unified_cycle29.nc`: analysis, background,
  truth, NoDA, observation, and observation-error fields;
- `results/`: per-variable error and timing CSVs;
- `free_run/`: the reused NoDA trajectory;
- `snapshots/`: the synthetic truth trajectory;
- `sde_tracking.nc`: EnSF reverse-SDE trajectories.

Generated results and logs are Git-ignored. They will not appear in a GitHub
fork and should not be committed. Transfer them separately with checksums if
another researcher needs the exact output files.

## 7. Validate the completed experiments

The all-cases Slurm script strictly validates EnSF against Table 7 and prints
an informational LETKF comparison after all eight runs. The same checks can be
repeated manually:

```bash
python amlcs/workflows/jack_report/check_results.py \
    --case all --method ensf --strict
python amlcs/workflows/jack_report/check_results.py \
    --case all --method letkf
```

This recomputes the report's unweighted horizontal RMSE, averages independently
calculated level RMSE values, averages across 30 cycles, and compares the result
with Table 7. The default strict relative tolerance is 10%.

Do not use `--strict` against Table 7 as the acceptance test for the new LETKF
runs. Table 7 contains Jack's mixed-layout production results, whereas these
runners consistently use the multivariate layout. Differences are expected and
must be reported, not treated as evidence that the workflow failed. Case 1 has
already completed successfully with `option_mask=1`; its level- and
cycle-averaged LETKF errors differ from Table 7 by approximately 35--53% across
the five variables. This is the reason new multivariate tuning is required.

To inspect one case without making differences fatal:

```bash
python amlcs/workflows/jack_report/check_results.py \
    --case 3 --method both
```

## 8. Reproduce case-1 Figures 1 and 2

After case 1 EnSF completes, partial EnSF-plus-NoDA figures can be generated:

```bash
python amlcs/workflows/jack_report/plot_case1.py --ensf-only
```

After both case-1 methods complete, generate the full figures:

```bash
python amlcs/workflows/jack_report/plot_case1.py
```

The figures are stored under:

```text
runs/jack_report/case1_linear/figures/
```

These figures show the corrected multivariate LETKF result. They are not
expected to be numerically identical to Jack's original Figures 1 and 2, which
were generated from the case-1 `option_mask=2` production run.

## 9. Case-2 normalization ambiguity

The default case-2 LETKF runner reproduces Jack's archived calculation and
Table 7, where `normalize_nonlinear=False`. Equation 16 in the written report
describes a standardized arctangent operator, which instead requires
`normalize_nonlinear=True`.

The canonical all-cases run follows the archived result. To test the written
equation separately without overwriting it, run inside a Slurm allocation:

```bash
python amlcs/workflows/jack_report/run_cases.py \
    --case 2 --method letkf --paper-spec --execute
```

That alternative writes under
`runs/jack_report/case2_arctan_paper_spec/`.

## 10. Troubleshooting and reporting changes

- If `run_py.sh` says to activate `amlcs`, run `source start_da_session.sh`.
- If preflight reports missing NetCDF or restart inputs, stop; do not submit a
  partial experiment.
- If an output directory already contains incomplete data, preserve it under a
  clearly labeled archive before starting a fresh run.
- Do not edit the provenance copies under
  `amlcs/workflows/provenance/emmanuella_attempt/submitted_configs/`; they are
  historical evidence, not active runners.
- Make active configuration changes only under
  `amlcs/workflows/jack_report/cases/`.
- Keep `option_mask=1` in every canonical LETKF runner. Treat a change to the
  block layout as a new experiment with a distinct output directory.
- Rerun preflight after every configuration or driver change.
- Commit source/configuration changes to your branch, push to your fork, and
  open a pull request. Do not include `runs/`, `logs/`, `.out`, or `.err` files.

When reporting a run, record the Git commit, Slurm job ID, runner SHA-256 from
`run_metadata.json`, the strict EnSF comparison, and the informational LETKF
comparison with Table 7.
