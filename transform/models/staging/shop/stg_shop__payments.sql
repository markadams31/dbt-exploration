with source as (

    select * from {{ source('shop', 'payments') }}

),

renamed as (

    select
        payment_id,
        order_id,
        method,
        cast(amount_cents as decimal(12, 2)) / 100 as amount,
        paid_at,
        _loaded_at as loaded_at
    from source

)

select * from renamed
