"""Plumbing commands for the lab environment. The story lives in the
notebooks; these just get the Docker stack into (and back to) a known-good
state:

    uv run setup      start the warehouse container and wait until healthy
    uv run check      verify docker, the ODBC driver, the container, and dbt
    uv run reset      restore raw seed data, drop dbt's schemas and artifacts
    uv run teardown   stop the container (--wipe also destroys the data volume)

Everything is Python, so it behaves identically on Windows, macOS and Linux.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from rich.console import Console

from lab.config import (
    DBT_SCHEMAS,
    REPO_ROOT,
    TRANSFORM_DIR,
    apply_lab_defaults,
    connect,
)

apply_lab_defaults()
console = Console()


def _compose(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _step(msg: str) -> None:
    console.print(f"... {msg}")


def setup() -> None:
    """Start the warehouse; wait until it is healthy (which includes the raw seed)."""
    _step("starting the warehouse (first run pulls the image, a few minutes)")
    result = _compose("up", "-d", "--wait")
    if result.returncode != 0:
        console.print(result.stderr)
        sys.exit(1)
    console.print("[green]✓[/green] warehouse healthy, raw schema seeded · open the notebooks")


def teardown() -> None:
    """Stop the container; pass --wipe to also destroy the data volume."""
    wipe = "--wipe" in sys.argv[1:]
    _step("stopping the warehouse" + (" and destroying its volume" if wipe else ""))
    _compose("down", *(["-v"] if wipe else []))
    console.print(
        "[green]✓[/green] stopped" + (" · run `uv run setup` for a fresh stack" if wipe else "")
    )


def check() -> None:
    """Verify everything the lab needs; say exactly how to fix what's missing."""
    ok = True

    def item(label: str, passed: bool, fix: str = "") -> None:
        nonlocal ok
        mark = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f" {mark} {label}")
        if not passed:
            ok = False
            if fix:
                console.print(f"    [dim]fix:[/dim] {fix}")

    item(
        "docker CLI",
        shutil.which("docker") is not None,
        "install Docker Desktop (Windows/macOS) or docker.io (Linux)",
    )
    if shutil.which("docker"):
        engine = subprocess.run(["docker", "info"], capture_output=True, check=False)
        item(
            "docker engine reachable",
            engine.returncode == 0,
            "start Docker Desktop / `systemctl start docker`; on Linux ensure your user is in the docker group",
        )

    try:
        import pyodbc

        drivers = [d for d in pyodbc.drivers() if "ODBC Driver 1" in d and "SQL Server" in d]
        item(
            f"SQL Server ODBC driver ({', '.join(drivers) or 'none found'})",
            bool(drivers),
            "Windows: winget install Microsoft.msodbcsql.18 · macOS: brew tap microsoft/mssql-release && brew install msodbcsql18 · "
            "Linux: packages.microsoft.com (see 'Running it' in the README)",
        )
    except ImportError:
        item("pyodbc importable", False, "run `uv sync`")

    ps = _compose("ps", "--services", "--filter", "status=running")
    running = set(ps.stdout.split()) if ps.returncode == 0 else set()
    item("mssql container running", "mssql" in running, "run `uv run setup`")

    if "mssql" in running:
        import pyodbc

        try:
            with connect() as conn:
                conn.execute("SELECT TOP 1 1 FROM raw.customers")
            reachable = True
        except pyodbc.Error:
            reachable = False
        item(
            "warehouse reachable as `transformer`",
            reachable,
            "the container may still be initialising; retry in ~30s, or `uv run teardown --wipe && uv run setup`",
        )

    parse = _dbt_quiet("parse")
    item(
        "dbt project parses and profile resolves",
        parse,
        "run `uv sync`; if it persists, `uv run dbt debug --project-dir transform --profiles-dir transform`",
    )

    sys.exit(0 if ok else 1)


def reset() -> None:
    """Restore raw seed data and remove everything dbt has built: warehouse
    schemas and local artifacts. Starts the container first if needed.
    Every notebook's first cell; must stay idempotent."""
    ps = _compose("ps", "--services", "--filter", "status=running")
    if "mssql" not in set(ps.stdout.split()):
        setup()
    _step("restoring raw seed data and dropping dbt schemas")
    from lab.shop import reseed_raw

    reseed_raw()
    _drop_dbt_schemas()
    # Notebook-written scratch models would otherwise leak into the next story.
    from lab import scratch

    scratch.clear()
    # Stale artifacts lie: run_results.json from a previous story would let a
    # notebook assert against runs it never made.
    for stale in (TRANSFORM_DIR / "target", TRANSFORM_DIR / "logs"):
        if stale.exists():
            shutil.rmtree(stale)
    console.print("[green]✓[/green] lab restored to its starting state")


def _dbt_quiet(*args: str) -> bool:
    """Run a dbt command suppressing all non-error output; True on success."""
    from dbt.cli.main import dbtRunner

    res = dbtRunner().invoke([*args, "--quiet", "--log-level", "error"])
    return res.success


def _drop_dbt_schemas() -> None:
    with connect() as conn:
        cursor = conn.cursor()
        for schema in DBT_SCHEMAS:
            # Views before tables: a view can depend on a table, never the
            # reverse here. No cross-schema dependencies exist among drops
            # because staging views read only from raw.
            for kind, drop in (("sys.views", "VIEW"), ("sys.tables", "TABLE")):
                rows = cursor.execute(
                    f"SELECT name FROM {kind} WHERE schema_id = SCHEMA_ID(?)", schema
                ).fetchall()
                for (name,) in rows:
                    cursor.execute(f"DROP {drop} [{schema}].[{name}]")
            if cursor.execute("SELECT SCHEMA_ID(?)", schema).fetchone()[0] is not None:
                cursor.execute(f"DROP SCHEMA [{schema}]")
