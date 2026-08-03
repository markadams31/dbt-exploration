-- The customer dimension, current state only: one row per customer as the
-- source knows them today. History is the snapshot's job (notebook 03).
with customers as (

    select * from {{ ref('stg_shop__customers') }}

),

states as (

    select * from {{ ref('au_states') }}

),

final as (

    select
        customers.customer_id,
        customers.company_name,
        customers.state_code,
        states.state_name,
        states.region,
        customers.segment,
        customers.credit_limit,
        customers.updated_at
    from customers
    left join states
        on customers.state_code = states.state_code

)

select * from final
