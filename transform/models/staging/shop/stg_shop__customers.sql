-- Staging: rename, retype, nothing else. One model per source table.
with source as (

    select * from {{ source('shop', 'customers') }}

),

renamed as (

    select
        customer_id,
        company_name,
        state as state_code,
        segment,
        cast(credit_limit_cents as decimal(12, 2)) / 100 as credit_limit,
        updated_at
    from source

)

select * from renamed
