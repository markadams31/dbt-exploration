"""Upstream chaos, one intention-named function at a time.

These helpers write to the raw landing zone the way the shop's systems would;
each call is the lab's stand-in for "something happened upstream that nobody
told the data team about". dbt never sees this module; it only ever sees the
tables afterwards. `uv run reset` undoes everything.
"""

from __future__ import annotations

import pandas as pd

from lab.config import connect


def run_sql(sql: str, *params):
    """Escape hatch for the probe catalog: arbitrary SQL against the warehouse.
    Returns rows for SELECTs, None otherwise."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, *params)
        return cursor.fetchall() if cursor.description else None


def reseed_raw() -> None:
    """Restore the raw landing zone to ground truth: the seed script,
    re-executed. The probe harness calls this between probes; `uv run reset`
    calls it too. sqlcmd-style GO separators are not T-SQL, so execute
    batch by batch, exactly as the container's init does."""
    import re

    from lab.config import RAW_SEED_SQL

    batches = re.split(r"^\s*GO\s*$", RAW_SEED_SQL.read_text(), flags=re.MULTILINE | re.IGNORECASE)
    with connect() as conn:
        cursor = conn.cursor()
        for batch in batches:
            if batch.strip():
                cursor.execute(batch)


def scalar(sql: str, *params):
    """First column of the first row: the shape most assertions want."""
    rows = run_sql(sql, *params)
    return rows[0][0] if rows else None


def df(sql: str) -> pd.DataFrame:
    """A query result as a DataFrame, for display in notebook cells."""
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [c[0] for c in cursor.description]
        return pd.DataFrame.from_records(cursor.fetchall(), columns=columns)


# --- orders ----------------------------------------------------------------


def place_order(
    order_id: int,
    customer_id: int,
    product_id: int,
    quantity: int,
    unit_price_cents: int,
    placed_at: str,
    loaded_at: str | None = None,
    status: str = "placed",
) -> None:
    """A new order lands in the warehouse. loaded_at defaults to placed_at
    (the loader keeping up). Pass it explicitly to open a gap between the two."""
    run_sql(
        """
        INSERT INTO raw.orders
            (order_id, customer_id, product_id, status, quantity,
             unit_price_cents, placed_at, updated_at, _loaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            order_id,
            customer_id,
            product_id,
            status,
            quantity,
            unit_price_cents,
            placed_at,
            placed_at,
            loaded_at or placed_at,
        ),
    )


def arrive_late(order_id: int, *, placed_at: str, loaded_at: str, **order) -> None:
    """The order that happened days ago but only just reached the warehouse:
    placed_at far behind loaded_at. The gap is the whole point."""
    place_order(order_id, placed_at=placed_at, loaded_at=loaded_at, **order)


def update_order_status(
    order_id: int, status: str, updated_at: str, loaded_at: str | None = None
) -> None:
    """The source updates an order in place; the loader re-lands the row."""
    run_sql(
        """
        UPDATE raw.orders
        SET status = ?, updated_at = ?, _loaded_at = ?
        WHERE order_id = ?
        """,
        (status, updated_at, loaded_at or updated_at, order_id),
    )


# --- customers -------------------------------------------------------------


def update_customer(customer_id: int, updated_at: str | None = None, **changes) -> None:
    """The source overwrites customer fields in place. updated_at moves only
    if a value is passed; upstream systems forget to bump it more often
    than anyone admits, and notebook 03 depends on being able to forget too."""
    cols = dict(changes)
    if updated_at is not None:
        cols["updated_at"] = updated_at
    assignments = ", ".join(f"{col} = ?" for col in cols)
    run_sql(
        f"UPDATE raw.customers SET {assignments} WHERE customer_id = ?",
        (*cols.values(), customer_id),
    )


def delete_customer(customer_id: int) -> None:
    """A hard delete: the row simply stops existing. No tombstone, no event."""
    run_sql("DELETE FROM raw.customers WHERE customer_id = ?", (customer_id,))


def insert_customer(
    customer_id: int,
    company_name: str,
    state: str,
    segment: str,
    credit_limit_cents: int,
    updated_at: str,
) -> None:
    """A customer appears: brand new, or a deleted one resurrected under
    its old key. The warehouse cannot tell the difference; that's scenario 5."""
    run_sql(
        """
        INSERT INTO raw.customers
            (customer_id, company_name, state, segment, credit_limit_cents, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (customer_id, company_name, state, segment, credit_limit_cents, updated_at),
    )


# --- schema-level chaos ----------------------------------------------------


def add_column(table: str, column_ddl: str) -> None:
    """The upstream release that adds a column, e.g. add_column("orders",
    "discount_cents int"). Nobody files a ticket about these."""
    run_sql(f"ALTER TABLE raw.[{table}] ADD {column_ddl}")
