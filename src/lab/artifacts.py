"""Read what dbt wrote about its own run.

Every invocation leaves JSON artifacts in transform/target/: run_results.json
(what happened to each node) and manifest.json (the compiled project and its
DAG). The notebooks assert against these instead of trusting log output.
Read them immediately after the run that produced them: the next invocation
overwrites both.
"""

from __future__ import annotations

import itertools
import json
import math

from lab.config import TRANSFORM_DIR

TARGET = TRANSFORM_DIR / "target"


def run_results() -> dict[str, dict]:
    """Outcome per node of the most recent invocation, keyed by unique_id.

    {"model.shop.fct_orders": {"status": "success", "rows": 3, "message": None}}
    Statuses: success/error for models, pass/fail/warn/error for tests.
    """
    raw = json.loads((TARGET / "run_results.json").read_text())
    return {
        r["unique_id"]: {
            "status": r["status"],
            "rows": (r.get("adapter_response") or {}).get("rows_affected"),
            "message": r.get("message"),
        }
        for r in raw["results"]
    }


def elapsed() -> float:
    """Wall-clock seconds the most recent invocation took, as dbt measured it."""
    return json.loads((TARGET / "run_results.json").read_text())["elapsed_time"]


def freshness() -> dict[str, str]:
    """Status per source from the most recent `dbt source freshness` run,
    keyed by source table: {"orders": "error"}. Statuses: pass/warn/error.
    Read from sources.json, written beside run_results.json."""
    raw = json.loads((TARGET / "sources.json").read_text())
    return {r["unique_id"].split(".")[-1]: r["status"] for r in raw["results"]}


def manifest() -> dict:
    return json.loads((TARGET / "manifest.json").read_text())


def lineage_edges() -> set[tuple[str, str]]:
    """Every parent → child edge in the project DAG, by short name (sources
    as raw.<table>), the ground truth for the drawing below."""
    m = manifest()
    keep = ("model.", "seed.", "snapshot.", "source.")

    def short(uid: str) -> str:
        kind, name = uid.split(".")[0], uid.split(".")[-1]
        return f"raw.{name}" if kind == "source" else name

    return {
        (short(parent), short(child))
        for parent, children in m["child_map"].items()
        if parent.startswith(keep)
        for child in children
        if child.startswith(keep)
    }


def lineage_figure():
    """The project DAG, drawn from the manifest at the moment of the call:
    a diagram that is regenerated rather than maintained, so it cannot drift
    from the code. Layout is derived too: column = distance from a source,
    row order follows each node's parents."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch

    edges = sorted(lineage_edges())
    parents: dict[str, set[str]] = {n: set() for edge in edges for n in edge}
    for parent, child in edges:
        parents[child].add(parent)

    def depth(n: str) -> int:
        return 1 + max((depth(p) for p in parents[n]), default=-1)

    columns: dict[int, list[str]] = {}
    for n in sorted(parents):
        columns.setdefault(depth(n), []).append(n)

    pos: dict[str, tuple[float, float]] = {}
    for c, names in sorted(columns.items()):
        ideal = {
            n: (sum(pos[p][1] for p in parents[n]) / len(parents[n]) if parents[n] else 0.0)
            for n in names
        }
        names.sort(key=lambda n: (-ideal[n], n))
        spaced = sorted(ideal.values(), reverse=True)
        if all(a - b >= 1 for a, b in itertools.pairwise(spaced)):
            for n in names:  # the rows are free: sit level with the parents
                pos[n] = (float(c), ideal[n])
        else:  # rows would collide: pack the column around its middle
            for i, n in enumerate(names):
                pos[n] = (float(c), (len(names) - 1) / 2 - i)

    def style(n: str) -> tuple[str, str]:
        # same palette as the hand-drawn diagrams: raw purple, marts green
        for prefix, fill, line in (
            ("raw.", "#fbefff", "#8250df"),
            ("customers_snapshot", "#fff8c5", "#9a6700"),
            ("fct_", "#dafbe1", "#116329"),
            ("dim_", "#dafbe1", "#116329"),
        ):
            if n.startswith(prefix):
                return fill, line
        return "#ddf4ff", "#0969da"  # staging, seed, intermediate: views

    FONT = 9  # pt; box and arrow geometry below is sized from it
    fig, ax = plt.subplots(figsize=(11, 4.2))
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    xs = [x for x, _ in pos.values()]
    ys = [y for _, y in pos.values()]
    ax.set_xlim(min(xs) - 0.7, max(xs) + 0.7)
    ax.set_ylim(min(ys) - 0.7, max(ys) + 0.7)
    # data-unit → point scales, so arrows can stop at a box's actual border
    x_pt = 11 * 0.96 * 72 / (max(xs) - min(xs) + 1.4)
    y_pt = 4.2 * 0.96 * 72 / (max(ys) - min(ys) + 1.4)

    def border(label: str, ux: float, uy: float) -> float:
        """Points from a box's centre to its border, along direction (ux, uy)."""
        half_w = len(label) / 2 * FONT * 0.62 + 8  # monospace ≈ 0.62 em/char
        half_h = FONT * 0.55 + 8
        along = [half_w / abs(ux) if ux else math.inf, half_h / abs(uy) if uy else math.inf]
        return min(along) + 3

    for p, c in edges:
        vx = (pos[c][0] - pos[p][0]) * x_pt
        vy = (pos[c][1] - pos[p][1]) * y_pt
        ux, uy = vx / math.hypot(vx, vy), vy / math.hypot(vx, vy)
        # edges that skip a column bow slightly, threading between the rows
        rad = -0.2 if pos[c][0] - pos[p][0] >= 2 else 0.0
        ax.add_patch(
            FancyArrowPatch(
                pos[p],
                pos[c],
                arrowstyle="-|>",
                mutation_scale=11,
                color="#59636e",
                connectionstyle=f"arc3,rad={rad}",
                shrinkA=border(p, ux, uy),
                shrinkB=border(c, ux, uy),
            )
        )
    for n, xy in pos.items():
        fill, line = style(n)
        ax.text(
            *xy,
            n,
            ha="center",
            va="center",
            fontsize=FONT,
            family="monospace",
            color="#1f2328",
            bbox={"boxstyle": "round,pad=0.45", "facecolor": fill, "edgecolor": line},
        )
    ax.axis("off")
    plt.close(fig)  # the notebook shows the returned figure exactly once
    return fig
