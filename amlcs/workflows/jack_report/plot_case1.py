#!/usr/bin/env python3
"""Reproduce report Figures 1 and 2 from the all-linear experiment."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

from check_results import levels_for, output_dir as run_output_dir


WORKFLOW_DIR = Path(__file__).resolve().parent
REPO_ROOT = WORKFLOW_DIR.parents[2]
CYCLES = 30
COLORS = {"ensf": "#1f77b4", "letkf": "#ff7f0e"}
LABELS = {"ensf": "EnSF", "letkf": "LETKF"}

PANEL_INFO = {
    "UG1": r"(a) Zonal Wind [$u$] (m s$^{-1}$)" "\n" "Level-Averaged",
    "VG1": r"(b) Meridional Wind [$v$] (m s$^{-1}$)" "\n" "Level-Averaged",
    "TG1": r"(c) Temperature [$T$] (K)" "\n" "Level-Averaged",
    "PSG1": r"(d) Surface Pressure [$p_s$] (log($p_s/P_0$))",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "mathtext.fontset": "stix",
            "axes.titleweight": "bold",
            "axes.linewidth": 1.0,
            "xtick.direction": "out",
            "ytick.direction": "out",
        }
    )


def rmse(dataset: Dataset, prefix: str, variable: str, level: int) -> float:
    state = np.asarray(dataset.variables[f"{prefix}_{variable}_lev{level}"][:])
    truth = np.asarray(dataset.variables[f"truth_{variable}_lev{level}"][:])
    return float(np.sqrt(np.mean((state - truth) ** 2)))


def read_all_series(
    run_dir: Path, variables: tuple[str, ...]
) -> dict[str, dict[str, np.ndarray]]:
    paths = [run_dir / f"unified_cycle{cycle}.nc" for cycle in range(CYCLES)]
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"{run_dir} is missing {len(missing)} of {CYCLES} unified cycle files"
        )

    values = {
        variable: {prefix: [] for prefix in ("xa_mean", "xb_mean", "noda")}
        for variable in variables
    }
    for path in paths:
        with Dataset(path, "r") as dataset:
            for variable in variables:
                levels = levels_for(variable)
                for prefix in values[variable]:
                    level_errors = [
                        rmse(dataset, prefix, variable, level) for level in levels
                    ]
                    values[variable][prefix].append(float(np.mean(level_errors)))

    # Jack's plots begin with the pre-assimilation error, then show the 30
    # archived cycles. Anchor every curve at that same cycle-0 NoDA value.
    return {
        variable: {
            prefix: np.asarray(
                [values[variable]["noda"][0], *series], dtype=float
            )
            for prefix, series in variable_values.items()
        }
        for variable, variable_values in values.items()
    }


def style_axis(axis: plt.Axes) -> None:
    axis.set_yscale("log")
    axis.set_xlim(-0.5, CYCLES + 0.5)
    axis.set_xticks(np.arange(0, CYCLES + 1, 5))
    axis.grid(True, which="major", color="#d0d0d0", linewidth=0.8)
    axis.grid(True, which="minor", axis="y", color="#e8e8e8", linewidth=0.5)
    axis.set_axisbelow(True)


def draw_curves(
    axis: plt.Axes,
    series: dict[str, dict[str, np.ndarray]],
    *,
    show_noda: bool = True,
) -> None:
    cycles = np.arange(CYCLES + 1)
    if show_noda:
        axis.plot(
            cycles,
            series["ensf"]["noda"],
            color="black",
            linewidth=2.4,
            label="NoDA",
        )
    for method in ("ensf", "letkf"):
        if method not in series:
            continue
        axis.plot(
            cycles,
            series[method]["xa_mean"],
            color=COLORS[method],
            linewidth=2.4,
            label=f"{LABELS[method]} Analysis",
        )
        axis.plot(
            cycles,
            series[method]["xb_mean"],
            color=COLORS[method],
            linewidth=2.4,
            linestyle="--",
            label=f"{LABELS[method]} Background",
        )


def save_figure1(
    data: dict[str, dict[str, dict[str, np.ndarray]]], output: Path
) -> None:
    figure, axis = plt.subplots(figsize=(9.0, 4.8))
    draw_curves(axis, data["TRG1"])
    style_axis(axis)
    axis.set_xlabel("Assimilation Cycle")
    axis.set_ylabel("RMSE")
    axis.set_title(
        r"Specific Humidity [$q$] (g kg$^{-1}$)" "\n" "Level-Averaged",
        pad=12,
    )
    handles, labels = axis.get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncol=len(labels),
        frameon=False,
        bbox_to_anchor=(0.5, 1.02),
    )
    figure.tight_layout(rect=(0, 0, 1, 0.91))
    figure.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(figure)


def save_figure2(
    data: dict[str, dict[str, dict[str, np.ndarray]]], output: Path
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(9.2, 6.2), sharex=True)
    variables = ("UG1", "VG1", "TG1", "PSG1")
    for axis, variable in zip(axes.flat, variables):
        draw_curves(axis, data[variable])
        style_axis(axis)
        axis.set_title(PANEL_INFO[variable], fontsize=11, pad=10)

    axes[0, 0].set_ylabel("RMSE")
    axes[1, 0].set_ylabel("RMSE")
    axes[1, 0].set_xlabel("Assimilation Cycle")
    axes[1, 1].set_xlabel("Assimilation Cycle")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncol=len(labels),
        frameon=False,
        bbox_to_anchor=(0.5, 1.01),
    )
    figure.tight_layout(rect=(0, 0, 1, 0.91), h_pad=1.7, w_pad=2.0)
    figure.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ensf-only",
        action="store_true",
        help="make partial figures using EnSF and NoDA without requiring LETKF",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "runs" / "jack_report" / "case1_linear" / "figures",
    )
    args = parser.parse_args()

    methods = ["ensf"] if args.ensf_only else ["ensf", "letkf"]
    variables = ("TRG1", "UG1", "VG1", "TG1", "PSG1")
    method_data = {
        method: read_all_series(run_output_dir("1", method), variables)
        for method in methods
    }
    data = {
        variable: {
            method: method_data[method][variable] for method in methods
        }
        for variable in variables
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "partial_ensf_noda" if args.ensf_only else "reproduced"
    outputs = [
        args.output_dir / f"figure1_{suffix}.png",
        args.output_dir / f"figure2_{suffix}.png",
    ]
    configure_style()
    save_figure1(data, outputs[0])
    save_figure2(data, outputs[1])
    for output in outputs:
        print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
