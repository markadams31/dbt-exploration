-- Ground truth for the raw landing zone. Runs once at container start and
-- again on every `uv run reset`, so it must be fully idempotent: drop every
-- table in raw (notebooks mutate them: extra columns, deleted rows), then
-- rebuild from scratch. Executed with -d warehouse.
--
-- The fiction: an EL pipeline lands these four tables hourly from the shop's
-- operational database. dbt's job starts here. _loaded_at is the loader's
-- own stamp: when the row reached the warehouse, not when the event happened.
-- The gap between those two clocks powers half the scenarios in this lab.

IF SCHEMA_ID('raw') IS NOT NULL
BEGIN
    -- Landing zones have no foreign keys (loaders write tables independently),
    -- so plain DROP TABLE per table is enough.
    DECLARE @sql nvarchar(max) = N'';
    SELECT @sql += N'DROP TABLE ' + QUOTENAME(s.name) + N'.' + QUOTENAME(t.name) + N';'
    FROM sys.tables t
    JOIN sys.schemas s ON t.schema_id = s.schema_id
    WHERE s.name = N'raw';
    EXEC sp_executesql @sql;
END
ELSE
    EXEC (N'CREATE SCHEMA raw');
GO

-- Loose landing-zone typing on purpose: money is integer cents, state is a
-- bare code, nothing is NOT NULL. Tightening this up is dbt's job, downstream.
CREATE TABLE raw.customers (
    customer_id        int,
    company_name       nvarchar(100),
    state              char(3),
    segment            nvarchar(20),
    credit_limit_cents int,
    updated_at         datetime2(0)
);

CREATE TABLE raw.products (
    product_id       int,
    sku              nvarchar(20),
    product_name     nvarchar(100),
    category         nvarchar(30),
    unit_price_cents int,
    updated_at       datetime2(0)
);

CREATE TABLE raw.orders (
    order_id         int,
    customer_id      int,
    product_id       int,
    status           nvarchar(20),
    quantity         int,
    unit_price_cents int,          -- price at order time; products.unit_price_cents may move later
    placed_at        datetime2(0),
    updated_at       datetime2(0),
    _loaded_at       datetime2(0)
);

CREATE TABLE raw.payments (
    payment_id   int,
    order_id     int,
    method       nvarchar(20),
    amount_cents int,
    paid_at      datetime2(0),
    _loaded_at   datetime2(0)
);
GO

INSERT INTO raw.customers (customer_id, company_name, state, segment, credit_limit_cents, updated_at) VALUES
    (1, N'Acme Pty Ltd',        'NSW', N'wholesale', 5000000, '2026-06-02T08:00:00'),
    (2, N'Bunbury Hardware',    'WA',  N'retail',    1500000, '2026-06-02T08:00:00'),
    (3, N'Coastal Traders',     'QLD', N'wholesale', 3500000, '2026-06-10T09:30:00'),
    (4, N'Dandenong Motors',    'VIC', N'trade',     2000000, '2026-06-02T08:00:00'),
    (5, N'Esperance Fisheries', 'WA',  N'wholesale', 2500000, '2026-06-18T14:15:00'),
    (6, N'Fremantle Freight',   'WA',  N'trade',     3000000, '2026-06-02T08:00:00'),
    (7, N'Geelong Textiles',    'VIC', N'retail',    1000000, '2026-06-25T11:45:00'),
    (8, N'Hobart Provedores',   'TAS', N'retail',     800000, '2026-06-02T08:00:00');
GO

INSERT INTO raw.products (product_id, sku, product_name, category, unit_price_cents, updated_at) VALUES
    (1, N'SKU-1001', N'Cordless Drill 18V',    N'tools',    18900, '2026-06-01T07:00:00'),
    (2, N'SKU-1002', N'Claw Hammer',           N'tools',     3450, '2026-06-01T07:00:00'),
    (3, N'SKU-1003', N'Safety Goggles',        N'safety',    1275, '2026-06-01T07:00:00'),
    (4, N'SKU-1004', N'Hi-Vis Vest',           N'safety',    2200, '2026-06-01T07:00:00'),
    (5, N'SKU-1005', N'Extension Ladder 3.8m', N'access',   44900, '2026-06-01T07:00:00'),
    (6, N'SKU-1006', N'Workbench 1.8m',        N'workshop', 32900, '2026-06-01T07:00:00');
GO

-- July 2026. Statuses: placed → shipped → delivered, or cancelled.
-- updated_at moves when the status does; _loaded_at trails updated_at by
-- minutes (the hourly loader).
INSERT INTO raw.orders (order_id, customer_id, product_id, status, quantity, unit_price_cents, placed_at, updated_at, _loaded_at) VALUES
    ( 1, 1, 1, N'delivered', 2, 18900, '2026-07-01T09:14:00', '2026-07-04T10:00:00', '2026-07-04T10:05:00'),
    ( 2, 3, 2, N'delivered',10,  3450, '2026-07-01T11:02:00', '2026-07-04T15:30:00', '2026-07-04T16:05:00'),
    ( 3, 2, 3, N'delivered', 5,  1275, '2026-07-02T10:20:00', '2026-07-06T09:10:00', '2026-07-06T10:05:00'),
    ( 4, 4, 5, N'shipped',   1, 44900, '2026-07-03T14:45:00', '2026-07-05T08:20:00', '2026-07-05T09:05:00'),
    ( 5, 5, 4, N'delivered',12,  2200, '2026-07-03T16:01:00', '2026-07-07T11:40:00', '2026-07-07T12:05:00'),
    ( 6, 1, 6, N'shipped',   1, 32900, '2026-07-05T08:55:00', '2026-07-06T13:15:00', '2026-07-06T14:05:00'),
    ( 7, 6, 1, N'delivered', 3, 18900, '2026-07-06T09:40:00', '2026-07-09T10:25:00', '2026-07-09T11:05:00'),
    ( 8, 7, 2, N'cancelled', 6,  3450, '2026-07-06T13:22:00', '2026-07-07T09:00:00', '2026-07-07T09:05:00'),
    ( 9, 8, 3, N'delivered', 8,  1275, '2026-07-07T15:09:00', '2026-07-10T14:50:00', '2026-07-10T15:05:00'),
    (10, 2, 4, N'shipped',  20,  2200, '2026-07-08T10:30:00', '2026-07-09T16:45:00', '2026-07-09T17:05:00'),
    (11, 3, 1, N'delivered', 1, 18900, '2026-07-09T09:05:00', '2026-07-12T10:15:00', '2026-07-12T11:05:00'),
    (12, 5, 2, N'placed',   15,  3450, '2026-07-10T11:47:00', '2026-07-10T11:47:00', '2026-07-10T12:05:00'),
    (13, 4, 3, N'delivered',10,  1275, '2026-07-10T14:12:00', '2026-07-14T09:35:00', '2026-07-14T10:05:00'),
    (14, 1, 5, N'shipped',   2, 44900, '2026-07-12T10:02:00', '2026-07-13T15:20:00', '2026-07-13T16:05:00'),
    (15, 6, 6, N'delivered', 1, 32900, '2026-07-13T09:31:00', '2026-07-16T11:05:00', '2026-07-16T12:05:00'),
    (16, 7, 1, N'placed',    2, 18900, '2026-07-14T16:20:00', '2026-07-14T16:20:00', '2026-07-14T17:05:00'),
    (17, 8, 2, N'delivered',12,  3450, '2026-07-15T08:44:00', '2026-07-18T10:40:00', '2026-07-18T11:05:00'),
    (18, 2, 5, N'cancelled', 1, 44900, '2026-07-15T13:55:00', '2026-07-16T09:15:00', '2026-07-16T10:05:00'),
    (19, 3, 6, N'shipped',   2, 32900, '2026-07-16T10:18:00', '2026-07-17T14:30:00', '2026-07-17T15:05:00'),
    (20, 5, 3, N'delivered',25,  1275, '2026-07-17T11:36:00', '2026-07-21T09:20:00', '2026-07-21T10:05:00'),
    (21, 1, 2, N'delivered', 8,  3450, '2026-07-19T09:27:00', '2026-07-22T13:45:00', '2026-07-22T14:05:00'),
    (22, 4, 4, N'shipped',  10,  2200, '2026-07-20T14:53:00', '2026-07-21T16:10:00', '2026-07-21T17:05:00'),
    (23, 6, 3, N'placed',   15,  1275, '2026-07-21T10:41:00', '2026-07-21T10:41:00', '2026-07-21T11:05:00'),
    (24, 7, 5, N'delivered', 1, 44900, '2026-07-22T09:58:00', '2026-07-25T10:30:00', '2026-07-25T11:05:00'),
    (25, 8, 6, N'shipped',   1, 32900, '2026-07-23T15:14:00', '2026-07-24T11:25:00', '2026-07-24T12:05:00'),
    (26, 2, 1, N'delivered', 2, 18900, '2026-07-24T10:07:00', '2026-07-27T09:45:00', '2026-07-27T10:05:00'),
    (27, 3, 4, N'placed',   30,  2200, '2026-07-25T13:29:00', '2026-07-25T13:29:00', '2026-07-25T14:05:00'),
    (28, 5, 6, N'delivered', 1, 32900, '2026-07-26T09:12:00', '2026-07-29T10:50:00', '2026-07-29T11:05:00'),
    (29, 6, 2, N'shipped',  20,  3450, '2026-07-27T11:50:00', '2026-07-28T14:05:00', '2026-07-28T15:05:00'),
    (30, 8, 1, N'placed',    1, 18900, '2026-07-28T16:33:00', '2026-07-28T16:33:00', '2026-07-28T17:05:00');
GO

-- Every shipped or delivered order is paid in full; placed orders are not yet
-- paid; cancelled orders never were. Order #14 pays in two instalments; the
-- singular test must SUM per order, and this row is why.
INSERT INTO raw.payments (payment_id, order_id, method, amount_cents, paid_at, _loaded_at) VALUES
    ( 1,  1, N'card',          37800, '2026-07-01T09:15:00', '2026-07-01T10:05:00'),
    ( 2,  2, N'bank_transfer', 34500, '2026-07-02T08:30:00', '2026-07-02T09:05:00'),
    ( 3,  3, N'card',           6375, '2026-07-02T10:21:00', '2026-07-02T11:05:00'),
    ( 4,  4, N'bank_transfer', 44900, '2026-07-04T09:10:00', '2026-07-04T10:05:00'),
    ( 5,  5, N'card',          26400, '2026-07-03T16:02:00', '2026-07-03T17:05:00'),
    ( 6,  6, N'card',          32900, '2026-07-05T08:56:00', '2026-07-05T09:05:00'),
    ( 7,  7, N'paypal',        56700, '2026-07-06T09:41:00', '2026-07-06T10:05:00'),
    ( 8,  9, N'card',          10200, '2026-07-07T15:10:00', '2026-07-07T16:05:00'),
    ( 9, 10, N'bank_transfer', 44000, '2026-07-09T08:45:00', '2026-07-09T09:05:00'),
    (10, 11, N'card',          18900, '2026-07-09T09:06:00', '2026-07-09T10:05:00'),
    (11, 13, N'paypal',        12750, '2026-07-10T14:13:00', '2026-07-10T15:05:00'),
    (12, 14, N'bank_transfer', 44900, '2026-07-12T10:03:00', '2026-07-12T11:05:00'),
    (13, 14, N'bank_transfer', 44900, '2026-07-13T09:15:00', '2026-07-13T10:05:00'),
    (14, 15, N'card',          32900, '2026-07-13T09:32:00', '2026-07-13T10:05:00'),
    (15, 17, N'card',          41400, '2026-07-15T08:45:00', '2026-07-15T09:05:00'),
    (16, 19, N'bank_transfer', 65800, '2026-07-17T10:20:00', '2026-07-17T11:05:00'),
    (17, 20, N'card',          31875, '2026-07-17T11:37:00', '2026-07-17T12:05:00'),
    (18, 21, N'paypal',        27600, '2026-07-19T09:28:00', '2026-07-19T10:05:00'),
    (19, 22, N'card',          22000, '2026-07-21T09:40:00', '2026-07-21T10:05:00'),
    (20, 24, N'card',          44900, '2026-07-22T09:59:00', '2026-07-22T10:05:00'),
    (21, 25, N'bank_transfer', 32900, '2026-07-24T10:15:00', '2026-07-24T11:05:00'),
    (22, 26, N'card',          37800, '2026-07-24T10:08:00', '2026-07-24T11:05:00'),
    (23, 28, N'card',          32900, '2026-07-26T09:13:00', '2026-07-26T10:05:00'),
    (24, 29, N'bank_transfer', 69000, '2026-07-28T09:30:00', '2026-07-28T10:05:00');
GO
