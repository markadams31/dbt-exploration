"""Run dbt from a notebook exactly as you would from a shell.

dbt("build", "--select", "fct_orders") takes the same argv as the dbt CLI, so
every cell doubles as the command you would type, but returns a real result
object instead of an exit code to scrape.
"""

from __future__ import annotations

from dbt.cli.main import dbtRunner, dbtRunnerResult

from lab.config import TRANSFORM_DIR, apply_lab_defaults

apply_lab_defaults()


def dbt(*args: str, quiet: bool = False) -> dbtRunnerResult:
    """Invoke dbt; .success on the result is the verdict.

    A fresh dbtRunner per call: the runner is not re-entrant and carries
    state between invocations. quiet=True keeps errors only; the probe
    harness runs dozens of builds, and their story is told by artifacts,
    not by forty screens of logs.
    """
    argv = list(args)
    if quiet:
        argv += ["--quiet", "--log-level", "error"]
    return dbtRunner().invoke(argv)


def show(relpath: str) -> None:
    """Print a committed project file: the code the next dbt() call compiles."""
    print((TRANSFORM_DIR / relpath).read_text())
