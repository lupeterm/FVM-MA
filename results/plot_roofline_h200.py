"""Generate Julia H200 roofline plots from the measured GPU timings."""

from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results" / "NeoN-GPU.csv"
OUTPUT_DATA = ROOT / "results" / "roofline_h200_julia.csv"
OUTPUT_FIGURE = ROOT / "figures" / "roofline_h200_julia.svg"
OUTPUT_PROGRESSION_DATA = ROOT / "results" / "roofline_h200_julia_progression.csv"
OUTPUT_PROGRESSION_FIGURE = ROOT / "figures" / "roofline_h200_julia_progression.svg"

# NVIDIA H200 NVL, as specified in the thesis and NVIDIA's product sheet.
PEAK_FP64_GFLOPS = 30_000.0
PEAK_MEMORY_GBS = 4_800.0


def median(values: list[float]) -> float:
    values = sorted(values)
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return (values[middle - 1] + values[middle]) / 2


def traffic_counts(cell_dim: int, strategy: str) -> tuple[int, int, int, float]:
    """Return total FLOPs, reads, writes, and total-traffic AI for one mesh."""
    cells = cell_dim**3
    internal_faces = 3 * cell_dim**2 * (cell_dim - 1)
    boundary_faces = 6 * cell_dim**2

    if "Cell-Based" in strategy:
        flops = 16 * 2 * internal_faces + 6 * cells + 64 * boundary_faces
        reads = 44 * 2 * internal_faces + 13 * cells + 97 * boundary_faces
        writes = 24 * 2 * internal_faces + 24 * cells + 96 * boundary_faces
    else:
        flops = 42 * internal_faces + 64 * boundary_faces
        reads = 52 * internal_faces + 97 * boundary_faces
        writes = 96 * (internal_faces + boundary_faces)

    return flops, reads, writes, flops / (reads + writes)


def load_points(largest_only: bool = True) -> list[dict[str, float | str]]:
    with INPUT.open(newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["cells"]
            and row["node"] == "gpu-nvidia-h200"
            and row["julia_or_neon"] == "JuNe"
        ]

    if not rows:
        raise ValueError("No JuNe H200 GPU rows found")

    all_cells = sorted({int(float(row["cells"])) for row in rows})
    if largest_only:
        rows = [row for row in rows if int(float(row["cells"])) == all_cells[-1]]

    nnz_by_cells: dict[int, float] = {}
    for cell_count in all_cells:
        known_nnz = [
            float(row["nnz"])
            for row in rows
            if int(float(row["cells"])) == cell_count and row["nnz"]
        ]
        if known_nnz:
            nnz_by_cells[cell_count] = median(known_nnz)

    grouped_write_bandwidth: dict[tuple[int, str], list[float]] = defaultdict(list)
    for row in rows:
        cells = int(float(row["cells"]))
        if cells not in nnz_by_cells:
            continue
        time_ms = float(row["time_us"]) / 1_000.0
        # Some strategies omit nnz although it is mesh-invariant.
        nnz = float(row["nnz"]) if row["nnz"] else nnz_by_cells[cells]
        write_bandwidth_gbs = nnz * 8.0 / (time_ms * 1_000_000.0)
        grouped_write_bandwidth[(cells, row["strategy"])].append(write_bandwidth_gbs)

    points: list[dict[str, float | str]] = []
    for (cells, strategy), values in sorted(grouped_write_bandwidth.items()):
        cell_dim = round(cells ** (1.0 / 3.0))
        write_bandwidth = median(values)
        flops, reads, writes, arithmetic_intensity = traffic_counts(cell_dim, strategy)
        read_bandwidth = write_bandwidth * reads / writes
        total_bandwidth = read_bandwidth + write_bandwidth
        points.append(
            {
                "cells": cells,
                "cell_dim": cell_dim,
                "strategy": strategy,
                "write_bandwidth_gbs": write_bandwidth,
                "read_bandwidth_gbs": read_bandwidth,
                "total_bandwidth_gbs": total_bandwidth,
                "arithmetic_intensity_flop_per_byte": arithmetic_intensity,
                "achieved_gflops": arithmetic_intensity * total_bandwidth,
                "flops": flops,
                "read_bytes": reads,
                "written_bytes": writes,
                "runs": len(values),
            }
        )

    if not points:
        raise ValueError("No Julia H200 points with usable nnz metadata found")
    return points


def write_data(path: Path, points: list[dict[str, float | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(points[0]))
        writer.writeheader()
        writer.writerows(points)


def merge_face_points(points: list[dict[str, float | str]]) -> list[dict[str, float | str]]:
    """Merge Face-Based and Global Face-Based into one measured datapoint per mesh."""
    by_cells: dict[int, dict[str, dict[str, float | str]]] = defaultdict(dict)
    for point in points:
        by_cells[int(point["cells"])][str(point["strategy"])] = point

    merged: list[dict[str, float | str]] = []
    for cells, strategies in sorted(by_cells.items()):
        cell_point = strategies.get("Cell-Based")
        if cell_point is not None:
            merged.append(cell_point)

        face_points = [
            strategies[strategy]
            for strategy in ("Face-Based", "Global Face-Based")
            if strategy in strategies
        ]
        if not face_points:
            continue
        if len(face_points) == 1:
            merged.append(face_points[0])
            continue

        combined = dict(face_points[0])
        combined["strategy"] = "Face-Based + Global Face-Based"
        for field in (
            "write_bandwidth_gbs",
            "read_bandwidth_gbs",
            "total_bandwidth_gbs",
            "arithmetic_intensity_flop_per_byte",
            "achieved_gflops",
        ):
            combined[field] = sum(float(point[field]) for point in face_points) / len(face_points)
        combined["runs"] = sum(int(point["runs"]) for point in face_points)
        merged.append(combined)
    return merged


def plot(
    points: list[dict[str, float | str]],
    output_path: Path,
    title: str,
    progression: bool = False,
) -> None:
    """Write a Matplotlib roofline figure without point annotations."""
    x_min, x_max = 0.05, 100.0
    y_min, y_max = 1.0, 50_000.0

    fig, ax = plt.subplots(figsize=(10.8, 7.2), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    standard_x_ticks = [0.1, 1, 10, 100]
    standard_y_ticks = [1, 10, 100, 1_000, 10_000, 50_000]
    data_x_ticks = sorted({float(point["arithmetic_intensity_flop_per_byte"]) for point in points})
    data_y_ticks = sorted({float(point["achieved_gflops"]) for point in points})
    data_y_summary_tick = (data_y_ticks[0] + data_y_ticks[-1]) / 2 if len(data_y_ticks) > 1 else None
    data_y_summary_error = (data_y_ticks[-1] - data_y_ticks[0]) / 2 if len(data_y_ticks) > 1 else None
    if progression:
        ax.set_xticks(standard_x_ticks)
        ax.set_yticks(standard_y_ticks)
        ax.set_xticks(data_x_ticks, minor=True)
        ax.set_yticks(data_y_ticks, minor=True)
    else:
        ax.set_xticks(sorted(set(standard_x_ticks + data_x_ticks)))
        summary_ticks = [data_y_summary_tick] if data_y_summary_tick is not None else []
        ax.set_yticks(sorted(set(standard_y_ticks + summary_ticks)))
        ax.set_yticks(data_y_ticks, minor=True)

    def is_data_tick(value: float, data_ticks: list[float]) -> bool:
        return any(math.isclose(value, tick, rel_tol=1e-9, abs_tol=1e-12) for tick in data_ticks)

    def format_x_tick(value: float, _: float) -> str:
        return f"{value:.3f}" if is_data_tick(value, data_x_ticks) else f"{value:g}"

    def format_y_tick(value: float, _: float) -> str:
        if data_y_summary_tick is not None and math.isclose(value, data_y_summary_tick, rel_tol=1e-9, abs_tol=1e-12):
            return f"{data_y_summary_tick:.2f} ± {data_y_summary_error:.2f}"
        if not is_data_tick(value, data_y_ticks):
            return f"{value:g}" if value < 1_000 else f"{value / 1_000:g}k"
        if value < 1:
            return f"{value:.3f}"
        if value < 1_000:
            return f"{value:.2f}"
        return f"{value / 1_000:.2f}k"

    ax.xaxis.set_major_formatter(FuncFormatter(format_x_tick))
    ax.yaxis.set_major_formatter(FuncFormatter(format_y_tick))
    ax.grid(which="major", color="#c7c7c7", linestyle=":", linewidth=0.8)
    ax.tick_params(axis="both", which="major", labelsize=11, colors="#444")
    ax.tick_params(axis="both", which="minor", length=3, width=0.7, colors="#555", labelbottom=False, labelleft=False)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor", fontsize=10)
    ax.set_xlabel("Arithmetic intensity [FLOP/Byte]", fontsize=13, color="#222", labelpad=14)
    ax.set_ylabel("Attained FP64 performance [GFLOP/s]", fontsize=13, color="#222", labelpad=14)
    ax.set_title(title, fontsize=17, fontweight="semibold", color="#222", pad=16)

    crossover = PEAK_FP64_GFLOPS / PEAK_MEMORY_GBS
    ax.plot([x_min, crossover], [PEAK_MEMORY_GBS * x_min, PEAK_FP64_GFLOPS], color="#222", linewidth=2.5, zorder=2)
    ax.plot([crossover, x_max], [PEAK_FP64_GFLOPS, PEAK_FP64_GFLOPS], color="#222", linewidth=2.5, zorder=2)
    ax.text(crossover * 1.03, 1.35, f"crossover {crossover:.2f}", fontsize=9, color="#555")

    strategy_colors = {"Cell-Based": "#59a14f", "Face-Based + Global Face-Based": "#f28e2b"}
    strategy_markers = {"Cell-Based": "o", "Face-Based + Global Face-Based": "D"}
    min_dim = min(int(point["cell_dim"]) for point in points)
    max_dim = max(int(point["cell_dim"]) for point in points)

    def mesh_color(cell_dim: int) -> str:
        fraction = 1.0 if min_dim == max_dim else (math.log(cell_dim) - math.log(min_dim)) / (math.log(max_dim) - math.log(min_dim))
        start, end = (76, 120, 168), (228, 87, 86)
        channels = [round(start[i] + fraction * (end[i] - start[i])) for i in range(3)]
        return "#" + "".join(f"{channel:02x}" for channel in channels)

    if progression:
        grouped_points: dict[str, list[dict[str, float | str]]] = defaultdict(list)
        for point in points:
            grouped_points[str(point["strategy"])].append(point)
        for strategy, series in sorted(grouped_points.items()):
            series.sort(key=lambda item: int(item["cells"]))
            ax.plot(
                [float(point["arithmetic_intensity_flop_per_byte"]) for point in series],
                [float(point["achieved_gflops"]) for point in series],
                color=strategy_colors[strategy],
                linewidth=1.2,
                alpha=0.7,
                zorder=3,
            )

    for point in points:
        strategy = str(point["strategy"])
        color = mesh_color(int(point["cell_dim"]))
        ax.scatter(
            float(point["arithmetic_intensity_flop_per_byte"]),
            float(point["achieved_gflops"]),
            s=42,
            marker=strategy_markers[strategy],
            facecolor=color,
            edgecolor="#111",
            linewidth=0.8,
            zorder=4,
        )

    strategy_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#777", markeredgecolor="#111", markersize=7, label="Cell-Based"),
        Line2D([0], [0], marker="D", color="none", markerfacecolor="#777", markeredgecolor="#111", markersize=6, label="Face-Based + Global Face-Based"),
    ]
    if progression:
        strategy_handles.extend([
            Line2D([0], [0], marker="o", color="none", markerfacecolor=mesh_color(min_dim), markeredgecolor="#111", markersize=6, label=f"{min_dim}³"),
            Line2D([0], [0], marker="o", color="none", markerfacecolor=mesh_color(max_dim), markeredgecolor="#111", markersize=6, label=f"{max_dim}³"),
        ])
    ax.legend(
        handles=strategy_handles,
        title="Julia strategies" if not progression else "Julia strategies\nPoint color = mesh size",
        loc="lower right",
        frameon=True,
        facecolor="white",
        edgecolor="#bbbbbb",
        fontsize=9,
        title_fontsize=10,
        borderpad=0.8,
        labelspacing=0.6,
    )

    if progression:
        ax.text(0.01, -0.16, "Mesh progression from 1k to 64M cells", transform=ax.transAxes, fontsize=9, color="#555")
    else:
        ax.text(0.01, -0.16, "64M-cell LDC", transform=ax.transAxes, fontsize=9, color="#555")
    ax.text(1.0, -0.16, "Median of three H200 Julia runs; write bandwidth inferred from nnz × 8 bytes", transform=ax.transAxes, fontsize=9, color="#555", ha="right")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, format="svg", facecolor="white", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    all_points = merge_face_points(load_points(largest_only=False))
    largest_cells = max(int(point["cells"]) for point in all_points)
    largest_points = [point for point in all_points if int(point["cells"]) == largest_cells]
    write_data(OUTPUT_DATA, largest_points)
    write_data(OUTPUT_PROGRESSION_DATA, all_points)
    plot(largest_points, OUTPUT_FIGURE, "Julia matrix assembly roofline on NVIDIA H200 NVL")
    plot(all_points, OUTPUT_PROGRESSION_FIGURE, "Julia matrix assembly roofline progression on NVIDIA H200 NVL", progression=True)
    print(f"wrote {OUTPUT_DATA}")
    print(f"wrote {OUTPUT_FIGURE}")
    print(f"wrote {OUTPUT_PROGRESSION_DATA}")
    print(f"wrote {OUTPUT_PROGRESSION_FIGURE}")
