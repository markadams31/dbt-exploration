-- Singular test: a business rule too specific for any generic test.
-- Nothing ships unpaid: every shipped or delivered order must be covered
-- in full by its payments (instalments allowed, hence the SUM).
-- Returning zero rows is a pass; every row returned is a violation.
with orders as (

    select * from {{ ref('fct_orders') }}

),

paid as (

    select
        order_id,
        sum(amount) as amount_paid
    from {{ ref('stg_shop__payments') }}
    group by order_id

),

violations as (

    select
        orders.order_id,
        orders.status,
        orders.line_total,
        coalesce(paid.amount_paid, 0) as amount_paid
    from orders
    left join paid
        on orders.order_id = paid.order_id
    where
        orders.status in ('shipped', 'delivered')
        and coalesce(paid.amount_paid, 0) < orders.line_total

)

select * from violations
