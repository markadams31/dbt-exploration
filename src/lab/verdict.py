"""The lab's verdict language, shared by every notebook.

Two axes, deliberately separate:
  * outcome: how the run behaved. `graceful` (handled and said so),
    `loud` (failed with an explicit error), or `silent` (succeeded and
    said nothing).
  * damage: whether the data is actually wrong afterwards.

They are not the same thing. Some silent outcomes are harmless; the
dangerous quadrant is silent-and-damaging, and the colour scale below is
tuned to make exactly that quadrant impossible to skim past.
"""

from __future__ import annotations

import pandas as pd

# Explicit foreground + background so rows read correctly on light and dark
# themes (GitHub renders committed outputs in both).
PALETTE = {
    "graceful": "background-color: #dafbe1; color: #116329",
    "loud": "background-color: #fff8c5; color: #4d2d00",
    "benign": "background-color: #f6f8fa; color: #59636e",
    "damage": "background-color: #ffebe9; color: #82071e",
}


def tint(row: pd.Series) -> list[str]:
    """Row colour is risk to your data, not success or failure of the run."""
    if row["outcome"] in ("graceful", "loud"):
        kind = row["outcome"]
    else:
        kind = "damage" if row["data damage"] == "yes" else "benign"
    return [PALETTE[kind]] * len(row)


def style(matrix: pd.DataFrame):
    """Colour-tint a verdict table for display. Expects the columns
    `outcome` and `data damage` ("yes" / "—")."""
    return matrix.style.apply(tint, axis=1).hide(axis="index")
