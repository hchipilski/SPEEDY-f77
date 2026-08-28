# Reproducing the four reported cases

This is the audited reconstruction of the selected experiments in
`Jacks_defense_report.pdf`. It uses 80 ensemble members, 30 assimilation cycles,
two model days between observations, and full horizontal coverage (`s=1`).

| Case | Observations | EnSF | LETKF |
| --- | --- | --- | --- |
| 1 | Direct UG1, VG1, TG1, TRG1, PSG1 | inflation 1.00 | `r=3`, inflation 1.00 |
| 2 | Arctangent of all five fields | inflation 1.00 | `r=3`, inflation 1.00 |
| 3 | WDG1 and WSG1; direct TG1, TRG1, PSG1 | inflation 1.00 | `r=2`, inflation 1.15 |
| 4 | Direct PSG1 only | inflation 1.00 | `r=2`, inflation 1.30 |

EnSF uses `r=1` in these runner files only because the shared AMLCS driver
requires the column and includes it in folder names. The report correctly says
the score filter has no localization radius.

## Run

Create or activate the repository environment first. If it has not yet been
created, use the checked-in environment specification:

```bash
conda env create -f environment/conda/environment.yml
conda activate amlcs
```

Run the preflight from any directory:

```bash
python amlcs/workflows/jack_report/preflight.py
```

Preview all eight commands (the safe default):

```bash
python amlcs/workflows/jack_report/run_cases.py
```

Run one pair sequentially:

```bash
python amlcs/workflows/jack_report/run_cases.py --case 1 --method both --execute
```

For the first, all-linear experiment on Slurm, submit from the repository root:

```bash
sbatch slurm_jobs/jack_report_case1_linear.sh
```

The job runs the selected EnSF configuration followed by the selected LETKF
configuration, then checks both outputs against Table 7. They run sequentially
because the legacy AMLCS driver creates temporary build files in its working
directory. The job requests 16 forecast workers, 24 GB of memory, and a 48-hour
wall-time; its scheduler logs are `jack_case1_linear_<jobid>.out` and `.err` in
the submission directory.

Run a single method, or all cases:

```bash
python amlcs/workflows/jack_report/run_cases.py --case 3 --method letkf --execute
python amlcs/workflows/jack_report/run_cases.py --case all --method both --execute
```

These are expensive 80-member, 30-cycle jobs. `run_py.sh` writes console output
to timestamped files under `logs/`. Each driver invocation also copies its
runner to the output directory and writes `run_metadata.json` containing the
input SHA-256, active Git commit, and resolved run settings.

Outputs are isolated under:

```text
runs/jack_report/case1_linear/
runs/jack_report/case2_arctan/
runs/jack_report/case3_wind_tph/
runs/jack_report/case4_pressure_only/
```

## Check against the report

After runs finish, compute the report's level- and cycle-averaged analysis RMSE
and compare it with Table 7:

```bash
python amlcs/workflows/jack_report/check_results.py
python amlcs/workflows/jack_report/check_results.py --case 1 --strict
```

The reference values are tracked in `reference_metrics.csv`. `--strict` allows
a 10% relative difference by default; use `--rtol` to change it.

## Case-2 normalization audit

The default case-2 LETKF runner reproduces Jack's archived run and Table 7, for
which `normalize_nonlinear=False`. This conflicts with standardized Equation 16
in the report. To execute the written paper specification without overwriting
the archived-number reconstruction:

```bash
python amlcs/workflows/jack_report/run_cases.py \
  --case 2 --method letkf --paper-spec --execute
```

The alternative writes under `runs/jack_report/case2_arctan_paper_spec/`.
