#!/usr/bin/env python3
"""Compute report-style mean analysis RMSE and compare it with Table 7."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import sys


WORKFLOW_DIR = Path(__file__).resolve().parent
AMLCS_DIR = WORKFLOW_DIR.parents[1]
CASE_DIRS = {
    "1": "case1_linear",
    "2": "case2_arctan",
    "3": "case3_wind_tph",
    "4": "case4_pressure_only",
}
VARIABLES = ("UG1", "VG1", "TG1", "TRG1", "PSG1")


def levels_for(variable: str) -> range:
    if variable == "PSG1":
        return range(1)
    if variable == "TRG1":
        return range(2, 8)
    return range(8)


def read_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError(f"{path} must contain exactly one data row")
    return rows[0]


def output_dir(case: str, method: str) -> Path:
    config = WORKFLOW_DIR / "cases" / CASE_DIRS[case] / f"{method}.csv"
    row = read_row(config)
    settings_dir = (AMLCS_DIR / row["exp_settings"]).resolve()
    settings = read_row(settings_dir / "config.csv")
    token = int(round(100 * float(row["infla"])))
    folder = (
        f"{settings['code_path']}_{row['method'].strip()}_{int(row['r'])}_"
        f"{int(row['s'])}_{token}_mask_{int(row['option_mask'])}"
    )
    return (AMLCS_DIR / row["code"] / folder).resolve()


def reference_values() -> dict[tuple[str, str], dict[str, float]]:
    result = {}
    with (WORKFLOW_DIR / "reference_metrics.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        for row in csv.DictReader(stream):
            result[(row["case"], row["method"])] = {
                variable: float(row[variable]) for variable in VARIABLES
            }
    return result


def compute_metrics(run_dir: Path, cycles: int = 30) -> dict[str, float]:
    try:
        import numpy as np
        from netCDF4 import Dataset
    except ImportError as exc:
        raise RuntimeError(
            "check_results.py requires NumPy and netCDF4; activate the amlcs environment"
        ) from exc

    cycle_files = [run_dir / f"unified_cycle{cycle}.nc" for cycle in range(cycles)]
    missing = [path for path in cycle_files if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{run_dir} is missing {len(missing)} of {cycles} unified cycle files"
        )

    result = {}
    for variable in VARIABLES:
        per_level = []
        for level in levels_for(variable):
            per_cycle = []
            for cycle_file in cycle_files:
                with Dataset(cycle_file, "r") as dataset:
                    analysis_name = f"xa_mean_{variable}_lev{level}"
                    truth_name = f"truth_{variable}_lev{level}"
                    if analysis_name not in dataset.variables:
                        raise KeyError(f"{analysis_name} is missing from {cycle_file}")
                    if truth_name not in dataset.variables:
                        raise KeyError(f"{truth_name} is missing from {cycle_file}")
                    difference = (
                        np.asarray(dataset.variables[analysis_name][:])
                        - np.asarray(dataset.variables[truth_name][:])
                    )
                    per_cycle.append(float(np.sqrt(np.mean(difference ** 2))))
            per_level.append(np.asarray(per_cycle))
        result[variable] = float(np.mean(np.vstack(per_level)))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=["1", "2", "3", "4", "all"], default="all"
    )
    parser.add_argument(
        "--method", choices=["ensf", "letkf", "both"], default="both"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="return failure when any value differs by more than --rtol",
    )
    parser.add_argument(
        "--rtol", type=float, default=0.10,
        help="relative tolerance for --strict (default: 0.10)",
    )
    args = parser.parse_args()

    cases = list(CASE_DIRS) if args.case == "all" else [args.case]
    methods = ["ensf", "letkf"] if args.method == "both" else [args.method]
    reference = reference_values()
    fatal = False
    different = False

    print("case method variable       actual    table_7   rel_diff")
    for case in cases:
        for method in methods:
            run_dir = output_dir(case, method)
            try:
                actual = compute_metrics(run_dir)
            except (FileNotFoundError, KeyError, OSError, RuntimeError) as exc:
                print(f"case {case} {method}: {exc}", file=sys.stderr)
                fatal = True
                continue
            for variable in VARIABLES:
                expected = reference[(case, method)][variable]
                relative = abs(actual[variable] - expected) / abs(expected)
                marker = "OK" if relative <= args.rtol else "DIFF"
                print(
                    f"{case:>4} {method:<6} {variable:<8} "
                    f"{actual[variable]:>11.5g} {expected:>10.5g} "
                    f"{relative:>9.2%} {marker}"
                )
                if relative > args.rtol:
                    different = True

    return 1 if fatal or (args.strict and different) else 0


if __name__ == "__main__":
    raise SystemExit(main())
