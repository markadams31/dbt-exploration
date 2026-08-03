-- The number the business actually watches. Sits at the end of the DAG, so
-- every upstream mistake this lab manufactures eventually lands here.
-- Casts are explicit because this model has an enforced contract: SQL Server
-- widens SUM(decimal) to decimal(38,2), and the contract would refuse it.
with orders as (

    select * from {{ ref('fct_orders') }}

),

final as (

    select
        cast(placed_at as date) as order_date,
        count(*) as orders_placed,
        cast(sum(case when status <> 'cancelled' then line_total else 0 end)
             as decimal(14, 2)) as revenue
    from orders
    group by cast(placed_at as date)

)

select * from final
