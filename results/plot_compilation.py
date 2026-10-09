#!/usr/bin/env python3

import argparse
import csv
import math
import re
from html import escape
from pathlib import Path

TIME_PATTERN = re.compile(r"(?:(?P<minutes>\d+(?:\.\d+)?)m)?(?P<seconds>\d+(?:\.\d+)?)s")


def parse_duration(value: str) -> float:
    match = TIME_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"Unsupported duration: {value!r}")
    return 60 * float(match.group("minutes") or 0) + float(match.group("seconds"))


def format_duration(seconds: float) -> str:
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)}:{remainder:04.1f}"


def load_rows(path: Path) -> list[dict[str, object]]:
    with path.open(newline="") as source:
        rows = [row for row in csv.DictReader(source) if row["neon"].lower() == "true"]

    return [
        {
            **row,
            "real_seconds": parse_duration(row["real"]),
            "threads": int(row["threads"]),
            "julia": row["julia"].lower() == "true",
        }
        for row in rows
    ]


def plot(rows: list[dict[str, object]], output: Path) -> None:
    nodes = sorted({str(row["node"]) for row in rows})
    builds = sorted(
        {str(row["build"]) for row in rows},
        key=lambda value: (value != "gpu", value),
    )
    threads = sorted({int(row["threads"]) for row in rows})
    lookup = {
        (str(row["node"]), str(row["build"]), int(row["threads"]), bool(row["julia"])): float(
            row["real_seconds"]
        )
        for row in rows
    }

    width = 1200
    height = 600
    margin_left = 80
    margin_right = 24
    panel_gap = 48
    panel_width = (width - margin_left - margin_right - panel_gap) / len(nodes)
    plot_top = 125
    plot_bottom = 465
    plot_height = plot_bottom - plot_top
    bar_width = 34
    # Seaborn "deep" palette, matching the usual whitegrid categorical look.
    colors = {False: "#4C72B0", True: "#DD8452"}
    labels = {False: "Without Julia", True: "With Julia"}
    text_color = "#262626"
    muted_text = "#6F6F6F"
    grid_color = "#D9D9D9"
    axis_color = "#CCCCCC"
    ymax = math.ceil(max(lookup.values()) / 60) * 60
    tick_step = 60
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<desc>Grouped bars compare real compilation time for Julia disabled and enabled, split into H100 and H200 node panels and grouped by build and thread count.</desc>",
        '<rect width="100%" height="100%" fill="#FFFFFF"/>',
        f'<g font-family="Arial, Helvetica, sans-serif" fill="{text_color}">',
    ]

    elements.append(
        '<text x="20" y="295" text-anchor="middle" font-size="14" transform="rotate(-90 20 295)">Real time (seconds)</text>'
    )

    for panel_index, node in enumerate(nodes):
        panel_left = margin_left + panel_index * (panel_width + panel_gap)
        panel_right = panel_left + panel_width
        group_padding = 50
        usable_width = panel_width - 2 * group_padding
        positions = [
            panel_left + group_padding + usable_width * fraction
            for fraction in (0.08, 0.35, 0.65, 0.92)
        ]
        categories = [(build, thread_count) for build in builds for thread_count in threads]
        elements.append(
            f'<text x="{panel_left + panel_width / 2:.1f}" y="103" text-anchor="middle" font-size="18" font-weight="600">{escape(node.upper())}</text>'
        )

        for tick in range(0, ymax + tick_step, tick_step):
            y = plot_bottom - tick / ymax * plot_height
            elements.append(
                f'<line x1="{panel_left:.1f}" y1="{y:.1f}" x2="{panel_right:.1f}" y2="{y:.1f}" stroke="{grid_color}" stroke-width="1"/>'
            )
            if panel_index == 0:
                elements.append(
                    f'<text x="{panel_left - 10:.1f}" y="{y + 5:.1f}" text-anchor="end" font-size="12" fill="{muted_text}">{tick}</text>'
                )

        elements.append(
            f'<line x1="{panel_left:.1f}" y1="{plot_bottom}" x2="{panel_right:.1f}" y2="{plot_bottom}" stroke="{axis_color}" stroke-width="1"/>'
        )
        for category_index, ((build, thread_count), x) in enumerate(zip(categories, positions)):
            elements.append(
                f'<text x="{x:.1f}" y="487" text-anchor="middle" font-size="12">{thread_count} threads</text>'
            )
            for julia in (False, True):
                value = lookup[(node, build, thread_count, julia)]
                bar_height = value / ymax * plot_height
                bar_x = x - bar_width - 2 if not julia else x + 2
                bar_y = plot_bottom - bar_height
                elements.extend(
                    [
                        f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width}" height="{bar_height:.1f}" rx="2" fill="{colors[julia]}">',
                        f'<title>{labels[julia]}, {node.upper()}, {build.upper()}, {thread_count} threads: {format_duration(value)}</title>',
                        "</rect>",
                        f'<text x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 7:.1f}" text-anchor="middle" font-size="10" fill="{text_color}">{format_duration(value)}</text>',
                    ]
                )

            if category_index == len(threads) - 1:
                midpoint = (positions[category_index - 1] + positions[category_index]) / 2
                elements.append(
                    f'<text x="{midpoint:.1f}" y="514" text-anchor="middle" font-size="13" font-weight="600">{escape(build.upper())}</text>'
                )
            elif category_index == len(categories) - 1:
                midpoint = (positions[category_index - 1] + positions[category_index]) / 2
                elements.append(
                    f'<text x="{midpoint:.1f}" y="514" text-anchor="middle" font-size="13" font-weight="600">{escape(build.upper())}</text>'
                )

        if panel_index == len(nodes) - 1:
            legend_width = 165
            legend_height = 58
            legend_x = panel_right - legend_width - 12
            legend_y = plot_top + 10
            elements.extend(
                [
                    f'<rect x="{legend_x:.1f}" y="{legend_y:.1f}" width="{legend_width}" height="{legend_height}" rx="3" fill="#FFFFFF" stroke="{axis_color}" stroke-width="1"/>',
                    f'<text x="{legend_x + 10:.1f}" y="{legend_y + 18:.1f}" font-size="11" font-weight="600">With(out) Julia</text>',
                ]
            )
            for index, julia in enumerate((False, True)):
                y = legend_y + 30 + index * 18
                elements.extend(
                    [
                        f'<rect x="{legend_x + 10:.1f}" y="{y:.1f}" width="12" height="12" rx="2" fill="{colors[julia]}"/>',
                        f'<text x="{legend_x + 30:.1f}" y="{y + 10:.1f}" font-size="11">{labels[julia]}</text>',
                    ]
                )

    elements.extend(
        [
            "</g>",
            "</svg>",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(elements) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot compilation time by node, thread count, and Julia usage.")
    parser.add_argument("input", nargs="?", type=Path, default=Path(__file__).with_name("compilation.csv"))
    parser.add_argument("output", nargs="?", type=Path, default=Path(__file__).with_name("compilation-real.svg"))
    args = parser.parse_args()
    plot(load_rows(args.input), args.output)


if __name__ == "__main__":
    main()
