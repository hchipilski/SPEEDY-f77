#!/usr/bin/env python3
"""Validate the four report configurations without importing AMLCS dependencies."""

from __future__ import annotations

import argparse
import ast
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

LINEAR_ERRORS = [0.42, 0.18, 0.46, 0.05, 0.006] * 2
ARCTAN_ERRORS = [0.025, 0.05, 0.01, 0.01, 0.005] * 2
ALL_DIRECT = [1] * 10
WIND_TPH = [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1]
PRESSURE_ONLY = [0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

EXPECTED = {
    ("1", "ensf"): dict(method="ReverseSDE", r=1, infla=1.0, option_mask=2,
                         nonlinear_obs=False, wind_nonlinear_operator=False,
                         obs_plc=ALL_DIRECT, err_obs=LINEAR_ERRORS),
    ("1", "letkf"): dict(method="LETKF", r=3, infla=1.0, option_mask=1,
                          nonlinear_obs=False, wind_nonlinear_operator=False,
                          obs_plc=ALL_DIRECT, err_obs=LINEAR_ERRORS),
    ("2", "ensf"): dict(method="ReverseSDE", r=1, infla=1.0, option_mask=2,
                         nonlinear_obs=True, wind_nonlinear_operator=False,
                         normalize_nonlinear=True, obs_plc=ALL_DIRECT,
                         err_obs=ARCTAN_ERRORS),
    # This False value reproduces Jack's archived LETKF run and Table 7. The
    # report equation instead says standardized; letkf_paper_spec.csv records
    # that alternative explicitly.
    ("2", "letkf"): dict(method="LETKF", r=3, infla=1.0, option_mask=1,
                          nonlinear_obs=True, wind_nonlinear_operator=False,
                          normalize_nonlinear=False, obs_plc=ALL_DIRECT,
                          err_obs=ARCTAN_ERRORS),
    ("3", "ensf"): dict(method="ReverseSDE", r=1, infla=1.0, option_mask=2,
                         nonlinear_obs=False, wind_nonlinear_operator=True,
                         obs_plc=WIND_TPH,
                         err_obs=LINEAR_ERRORS + [0.2, 1.0]),
    ("3", "letkf"): dict(method="LETKF", r=2, infla=1.15, option_mask=1,
                          nonlinear_obs=False, wind_nonlinear_operator=True,
                          obs_plc=WIND_TPH,
                          err_obs=LINEAR_ERRORS + [0.2, 1.0]),
    ("4", "ensf"): dict(method="ReverseSDE", r=1, infla=1.0, option_mask=2,
                         nonlinear_obs=False, wind_nonlinear_operator=False,
                         obs_plc=PRESSURE_ONLY, err_obs=LINEAR_ERRORS),
    ("4", "letkf"): dict(method="LETKF", r=2, infla=1.30, option_mask=1,
                          nonlinear_obs=False, wind_nonlinear_operator=False,
                          obs_plc=PRESSURE_ONLY, err_obs=LINEAR_ERRORS),
}


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise ValueError(f"invalid boolean {value!r}")


def parse_list(value: str, converter):
    return [converter(item.strip()) for item in value.split(",")]


def read_one_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 1:
        raise ValueError(f"expected one data row, found {len(rows)}")
    return rows[0]


def resolve_from_amlcs(value: str) -> Path:
    return (AMLCS_DIR / value).resolve()


def validate_driver(errors: list[str]) -> None:
    driver = AMLCS_DIR / "amlcs_da.py"
    tree = ast.parse(driver.read_text(encoding="utf-8"), filename=str(driver))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]

    observation_calls = [
        node for node in calls
        if isinstance(node.func, ast.Name) and node.func.id == "observation"
    ]
    get_instance_calls = [
        node for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get_instance"
    ]
    required_observation = {
        "nonlinear_obs", "scalefact", "normalize_nonlinear",
        "nonlinear_operator_type",
    }
    required_method = required_observation | {
        "wind_nonlinear_operator", "wind_err",
    }
    if not any(required_observation <= {kw.arg for kw in call.keywords}
               for call in observation_calls):
        errors.append("amlcs_da.py does not pass all nonlinear options to observation()")
    if not any(required_method <= {kw.arg for kw in call.keywords}
               for call in get_instance_calls):
        errors.append("amlcs_da.py does not pass all nonlinear/wind options to get_instance()")


def validate_inputs(settings_dir: Path, errors: list[str]) -> None:
    config_path = settings_dir / "config.csv"
    if not config_path.is_file():
        errors.append(f"missing experiment settings: {config_path}")
        return
    try:
        settings = read_one_row(config_path)
    except (OSError, ValueError) as exc:
        errors.append(f"invalid {config_path}: {exc}")
        return

    if int(settings["Nens"]) != 80 or int(settings["M"]) != 30:
        errors.append(
            f"{config_path} must specify Nens=80 and M=30, found "
            f"Nens={settings['Nens']} and M={settings['M']}"
        )

    ensemble_dir = settings_dir / "ensemble_0"
    for prefix, expected in (("ensemble_member_", 80), ("fort_", 80)):
        suffix = ".nc" if prefix == "ensemble_member_" else ".3"
        count = len(list(ensemble_dir.glob(f"{prefix}*{suffix}")))
        if count < expected:
            errors.append(
                f"{ensemble_dir} has {count} {prefix} inputs; at least {expected} required"
            )

    snapshots = settings_dir / "snapshots"
    for cycle in range(30):
        path = snapshots / f"reference_solution_{cycle}.nc"
        if not path.is_file():
            errors.append(f"missing truth snapshot: {path}")
            break

    executable = settings_dir / "model_local" / "imp.exe"
    if not executable.is_file():
        errors.append(f"missing SPEEDY executable: {executable}")


def validate_config(
    case: str,
    method: str,
    errors: list[str],
    *,
    filename: str | None = None,
    expected: dict | None = None,
    expected_code: str | None = None,
) -> tuple[Path, dict[str, str]]:
    path = WORKFLOW_DIR / "cases" / CASE_DIRS[case] / (filename or f"{method}.csv")
    try:
        row = read_one_row(path)
    except (OSError, ValueError) as exc:
        errors.append(f"invalid {path}: {exc}")
        return path, {}

    required = {
        "r", "s", "method", "exp_settings", "infla", "err_obs", "obs_plc",
        "list_snapshots", "code", "option_mask", "nonlinear_obs",
        "wind_nonlinear_operator", "scalefact", "normalize_nonlinear",
        "nonlinear_operator_type",
    }
    missing = sorted(required - row.keys())
    if missing:
        errors.append(f"{path} is missing columns: {', '.join(missing)}")
        return path, row

    try:
        actual = {
            "method": row["method"].strip(),
            "r": int(row["r"]),
            "infla": float(row["infla"]),
            "option_mask": int(row["option_mask"]),
            "nonlinear_obs": parse_bool(row["nonlinear_obs"]),
            "wind_nonlinear_operator": parse_bool(row["wind_nonlinear_operator"]),
            "normalize_nonlinear": parse_bool(row["normalize_nonlinear"]),
            "obs_plc": parse_list(row["obs_plc"], int),
            "err_obs": parse_list(row["err_obs"], float),
        }
    except (KeyError, ValueError) as exc:
        errors.append(f"{path} contains an invalid value: {exc}")
        return path, row

    for field, expected_value in (expected or EXPECTED[(case, method)]).items():
        if actual[field] != expected_value:
            errors.append(
                f"{path}: {field}={actual[field]!r}, expected {expected_value!r}"
            )

    if int(row["s"]) != 1:
        errors.append(f"{path}: report requires s=1")
    if row["nonlinear_operator_type"].strip() != "arctan":
        errors.append(f"{path}: nonlinear_operator_type must be arctan")
    if float(row["scalefact"]) != 1.0:
        errors.append(f"{path}: scalefact must be 1.0")
    expected_code_value = expected_code or f"../runs/jack_report/{CASE_DIRS[case]}"
    if row["code"].strip().rstrip("/") != expected_code_value:
        errors.append(f"{path}: code must be {expected_code_value}")

    return path, row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="only print failures")
    args = parser.parse_args()

    errors: list[str] = []
    validate_driver(errors)
    settings_dirs: set[Path] = set()
    outputs: set[tuple[str, str, int, int, int, int]] = set()

    for case in CASE_DIRS:
        for method in ("ensf", "letkf"):
            path, row = validate_config(case, method, errors)
            if not row:
                continue
            settings_dirs.add(resolve_from_amlcs(row["exp_settings"]))
            output_key = (
                row["code"].strip().rstrip("/"), row["method"].strip(),
                int(row["r"]), int(row["s"]),
                int(round(100 * float(row["infla"]))), int(row["option_mask"]),
            )
            if output_key in outputs:
                errors.append(f"output collision for {path}: {output_key}")
            outputs.add(output_key)

    paper_expected = dict(EXPECTED[("2", "letkf")])
    paper_expected["normalize_nonlinear"] = True
    paper_path, paper_row = validate_config(
        "2",
        "letkf",
        errors,
        filename="letkf_paper_spec.csv",
        expected=paper_expected,
        expected_code="../runs/jack_report/case2_arctan_paper_spec",
    )
    if paper_row:
        settings_dirs.add(resolve_from_amlcs(paper_row["exp_settings"]))
        paper_output = (
            paper_row["code"].strip().rstrip("/"), paper_row["method"].strip(),
            int(paper_row["r"]), int(paper_row["s"]),
            int(round(100 * float(paper_row["infla"]))),
            int(paper_row["option_mask"]),
        )
        if paper_output in outputs:
            errors.append(f"output collision for {paper_path}: {paper_output}")
        outputs.add(paper_output)

    for settings_dir in settings_dirs:
        validate_inputs(settings_dir, errors)

    if errors:
        print("Preflight FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(
            "Preflight passed: 8 canonical configs, the case-2 paper variant, "
            "driver wiring, and inputs are valid."
        )
        print("Expected outputs are isolated under runs/jack_report/<case>/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
