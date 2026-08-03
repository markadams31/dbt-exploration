-- Staging: rename, retype, currency conversion.  Cents become 
-- dollars exactly once here, so no downstream model ever 
-- divides by 100 again.
with source as (

    select * from {{ source('shop', 'orders') }}

),

renamed as (

    select
        order_id,
        customer_id,
        product_id,
        status,
        quantity,
        cast(unit_price_cents as decimal(12, 2)) / 100 as unit_price,
        placed_at,
        updated_at,
        _loaded_at as loaded_at
    from source

)

select * from renamed
