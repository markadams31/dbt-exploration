"""Constants shared by the lab's plumbing. One place knows how to reach the
warehouse and where the dbt project lives; everything else imports from here."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_DIR = REPO_ROOT / "transform"
RAW_SEED_SQL = REPO_ROOT / "docker" / "mssql" / "raw-seed.sql"

# Same throwaway credentials as transform/profiles.yml: the lab's single user.
# Port 14330 on purpose: see docker-compose.yml.
WAREHOUSE_ODBC = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=127.0.0.1,14330;"
    "DATABASE=warehouse;"
    "UID=transformer;PWD=Localdev_2024!;"
    "Encrypt=yes;TrustServerCertificate=yes"
)

# Every schema dbt materialises into. `uv run reset` drops exactly these:
# an explicit list, so nothing outside the lab's footprint can be touched.
# scratch holds notebook-written model variants; dbt_test__audit is where
# --store-failures keeps failing rows.
DBT_SCHEMAS = ("staging", "intermediate", "marts", "snapshots", "scratch", "dbt_test__audit")


def apply_lab_defaults() -> None:
    """Point dbt at the committed project and profile.
    setdefault: anything you export yourself wins."""
    os.environ.setdefault("DBT_PROJECT_DIR", str(TRANSFORM_DIR))
    os.environ.setdefault("DBT_PROFILES_DIR", str(TRANSFORM_DIR))


def connect():
    """Open an autocommit pyodbc connection to the warehouse.
    Autocommit because the helpers run DDL (DROP SCHEMA, ALTER TABLE), which
    SQL Server won't happily mix with an open implicit transaction."""
    import pyodbc

    return pyodbc.connect(WAREHOUSE_ODBC, autocommit=True)
