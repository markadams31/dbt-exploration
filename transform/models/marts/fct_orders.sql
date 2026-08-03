-- The order fact. Incremental: once this table is too big to rebuild hourly,
-- each run appends or updates only what changed since the last one.
--
-- The three config choices below are not obvious, and none of them is the
-- default. Notebook 02 is about why each one is what it is.
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id',
    on_schema_change='fail'
) }}

select
    order_id,
    customer_id,
    product_id,
    sku,
    category,
    status,
    quantity,
    unit_price,
    line_total,
    placed_at,
    updated_at,
    loaded_at
from {{ ref('int_orders__enriched') }}

{% if is_incremental() %}
where loaded_at > (select coalesce(max(loaded_at), '1900-01-01') from {{ this }})
{% endif %}
