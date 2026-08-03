"""Model files the notebooks write on the fly.

Some scenarios need a deliberately naive variant of a model: an incremental
model with the wrong watermark, a snapshot with the wrong strategy. Those
live in scratch/ folders *inside* the dbt project, so dbt compiles them like
any other file, but `uv run reset` deletes them and git never sees them:
the committed project only ever shows the recommended shapes.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from lab.config import TRANSFORM_DIR

MODELS = TRANSFORM_DIR / "models" / "scratch"
SNAPSHOTS = TRANSFORM_DIR / "snapshots" / "scratch"


def _write(directory: Path, filename: str, text: str) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / filename).write_text(text.strip() + "\n", encoding="utf-8")
    return filename


def model(name: str, sql: str) -> str:
    """Drop a model into the project; returns the filename for show-and-tell."""
    return _write(MODELS, f"{name}.sql", sql)


def yml(name: str, text: str) -> str:
    """Schema YAML alongside the scratch models (tests, contracts, unit tests)."""
    return _write(MODELS, f"{name}.yml", text)


def snapshot_yml(name: str, text: str) -> str:
    return _write(SNAPSHOTS, f"{name}.yml", text)


def clear() -> None:
    for directory in (MODELS, SNAPSHOTS):
        if directory.exists():
            shutil.rmtree(directory)
