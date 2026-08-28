#!/usr/bin/env python3
"""Print or execute the canonical commands for Jack's four reported cases."""

from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import subprocess
import sys


WORKFLOW_DIR = Path(__file__).resolve().parent
AMLCS_DIR = WORKFLOW_DIR.parents[1]
CASE_DIRS = {
    "1": "case1_linear",
    "2": "case2_arctan",
    "3": "case3_wind_tph",
    "4": "case4_pressure_only",
}


def config_for(case: str, method: str, paper_spec: bool) -> Path:
    filename = f"{method}.csv"
    if paper_spec and case == "2" and method == "letkf":
        filename = "letkf_paper_spec.csv"
    return WORKFLOW_DIR / "cases" / CASE_DIRS[case] / filename


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case", choices=["1", "2", "3", "4", "all"], default="all",
        help="case to run (default: all)",
    )
    parser.add_argument(
        "--method", choices=["ensf", "letkf", "both"], default="both",
        help="method to run (default: both)",
    )
    parser.add_argument(
        "--execute", action="store_true",
        help="run jobs sequentially; without this flag commands are only printed",
    )
    parser.add_argument(
        "--paper-spec", action="store_true",
        help="for case 2 LETKF, use standardized arctan from report Eq. 16",
    )
    parser.add_argument(
        "--skip-preflight", action="store_true",
        help="skip validation (not recommended)",
    )
    args = parser.parse_args()

    if args.paper_spec and args.case not in {"2", "all"}:
        parser.error("--paper-spec only affects case 2")

    if not args.skip_preflight:
        subprocess.run(
            [sys.executable, str(WORKFLOW_DIR / "preflight.py")],
            cwd=AMLCS_DIR,
            check=True,
        )

    cases = list(CASE_DIRS) if args.case == "all" else [args.case]
    methods = ["ensf", "letkf"] if args.method == "both" else [args.method]

    commands: list[list[str]] = []
    for case in cases:
        for method in methods:
            config = config_for(case, method, args.paper_spec)
            relative_config = config.relative_to(AMLCS_DIR)
            commands.append(["./run_py.sh", "amlcs_da.py", str(relative_config)])

    print(f"Working directory: {AMLCS_DIR}")
    for command in commands:
        print("  " + shlex.join(command))

    if not args.execute:
        print("Dry run only. Add --execute to run the commands sequentially.")
        return 0

    for command in commands:
        print(f"Executing: {shlex.join(command)}", flush=True)
        subprocess.run(command, cwd=AMLCS_DIR, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
