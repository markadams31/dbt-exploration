-- Intermediate: business joins with no aggregation. Orders learn what they
-- sold; line_total is computed exactly once, here.
with orders as (

    select * from {{ ref('stg_shop__orders') }}

),

products as (

    select * from {{ ref('stg_shop__products') }}

),

joined as (

    select
        orders.order_id,
        orders.customer_id,
        orders.product_id,
        products.sku,
        products.product_name,
        products.category,
        orders.status,
        orders.quantity,
        orders.unit_price,
        cast(orders.quantity * orders.unit_price as decimal(14, 2)) as line_total,
        orders.placed_at,
        orders.updated_at,
        orders.loaded_at
    from orders
    left join products
        on orders.product_id = products.product_id

)

select * from joined
