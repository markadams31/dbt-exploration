with source as (

    select * from {{ source('shop', 'products') }}

),

renamed as (

    select
        product_id,
        sku,
        product_name,
        category,
        cast(unit_price_cents as decimal(12, 2)) / 100 as unit_price,
        updated_at
    from source

)

select * from renamed
