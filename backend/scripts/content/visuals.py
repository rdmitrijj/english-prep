"""Draw Writing Task 1 charts and tables from their numbers (PLAN §6.9), so the picture and the data the examiner
reads can never disagree. Process diagrams and maps are hand-drawn SVGs; this script leaves them alone.

    python -m scripts.content.visuals render practice-writing-t1-bar-01
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402

from app.config import get_settings  # noqa: E402
from scripts.content.generate import finalize, save  # noqa: E402
from scripts.content.offline import load  # noqa: E402
from scripts.content.schema import Chart, CVisual  # noqa: E402

# Plain, exam-like styling: muted colours, light grid, no decoration.
COLOURS = ["#2f5d8a", "#c8553d", "#8aa63f", "#e0a526", "#7a5195", "#5b8e7d", "#9c9c9c"]
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.prop_cycle": matplotlib.cycler(color=COLOURS), "svg.hashsalt": "english-prep"})


def fmt(v: float) -> str:
    return f"{v:,.0f}" if v == int(v) else f"{v:,.1f}"


def draw(axes: list, chart: Chart) -> None:
    """Draw one chart on its axes (a pie chart takes one axis per series)."""
    if chart.type == "pie":
        for ax, sr in zip(axes, chart.series):
            ax.pie(sr.values, labels=[f"{c}\n{fmt(v)}%" for c, v in zip(chart.categories, sr.values)],
                   startangle=90, counterclock=False, colors=COLOURS, wedgeprops={"edgecolor": "white"})
            ax.set_title(sr.name, fontsize=10)
        return  # the chart title goes above all its pies once the layout is final (render)
    ax = axes[0]
    if chart.type == "table":
        ax.axis("off")
        ax.set_title(f"{chart.title}\n({chart.unit})", fontweight="bold")
        table = ax.table(cellText=[[fmt(sr.values[i]) for sr in chart.series] for i in range(len(chart.categories))],
                         rowLabels=chart.categories, colLabels=[sr.name for sr in chart.series], loc="upper center",
                         cellLoc="center", bbox=(0, 0, 1, 1))
        table.set_fontsize(10)
        return
    ax.set_title(chart.title, fontweight="bold", wrap=True)
    x = range(len(chart.categories))
    if chart.type == "line":
        for sr in chart.series:
            ax.plot(x, sr.values, marker="o", markersize=4, label=sr.name)
        ax.set_ylim(bottom=0)
    else:  # bar: grouped bars, one colour per series
        width = 0.8 / len(chart.series)
        for i, sr in enumerate(chart.series):
            ax.bar([xi + (i - (len(chart.series) - 1) / 2) * width for xi in x], sr.values, width, label=sr.name)
    ax.set_xticks(list(x), chart.categories, rotation=30 if max(map(len, chart.categories)) > 8 else 0, ha="right"
                  if max(map(len, chart.categories)) > 8 else "center")
    ax.set_ylabel(chart.unit)
    ax.grid(axis="y", color="#dddddd")
    ax.set_axisbelow(True)
    if len(chart.series) > 1:
        ax.legend(frameon=False, fontsize=9)


def render(visual: CVisual, out: Path) -> None:
    widths = [len(c.series) if c.type == "pie" else 2 for c in visual.charts]  # a pie is square, a chart is wide
    rows = max(len(c.categories) for c in visual.charts)
    height = 0.42 * (rows + 1) + 0.9 if all(c.type == "table" for c in visual.charts) else 4.4
    fig, axes = plt.subplots(1, sum(widths), figsize=(3.2 * sum(widths), height), squeeze=False)
    axes, cols, i = list(axes[0]), [], 0
    for c, w in zip(visual.charts, widths):  # merge the two cells a non-pie chart spans
        if c.type != "pie":
            gs = axes[i].get_gridspec()
            axes[i].remove()
            axes[i + 1].remove()
            cols.append([fig.add_subplot(gs[0, i:i + 2])])
        else:
            cols.append(axes[i:i + w])
        i += w
    for chart, ax in zip(visual.charts, cols):
        draw(ax, chart)
    pies = any(c.type == "pie" for c in visual.charts)
    fig.tight_layout(rect=(0, 0, 1, 0.88) if pies else None)
    for chart, ax in zip(visual.charts, cols):
        if chart.type == "pie":
            boxes = [a.get_position() for a in ax]
            top = max(b.y1 for b in boxes) + 0.07  # above the per-pie titles ("2000", "2020")
            fig.text((boxes[0].x0 + boxes[-1].x1) / 2, top, chart.title, ha="center", va="bottom", fontweight="bold",
                     fontsize="large")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, format="svg", bbox_inches="tight", metadata={"Date": None})
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m scripts.content.visuals")
    parser.add_argument("cmd", choices=["render"])
    parser.add_argument("slug")
    args = parser.parse_args()
    test = load(args.slug)
    for part in (p for s in test.sections for p in s.parts if p.writing and p.writing.visual):
        visual = part.writing.visual
        if visual.type in ("process", "map"):
            continue
        name = f"{args.slug}-t{part.number}.svg"
        render(visual, Path(get_settings().content_dir) / "media" / "visuals" / name)
        visual.url = f"/media/visuals/{name}"
        print(f"drew {visual.url}")
    save(finalize(test))
    print(f"{test.status.value}: {args.slug}  ({len(test.check_errors)} check errors)")
    for e in test.check_errors:
        print("  check:", e)


if __name__ == "__main__":
    main()
