{{
    config(
        materialized='incremental',
        unique_key='order_id',
        incremental_strategy='delete+insert'
    )
}}

select
    order_id,
    order_number,
    customer_id,
    status as order_status,
    currency,
    subtotal,
    tax_amount,
    shipping_amount,
    discount_amount,
    total_amount as order_value,
    created_at as order_created_at,
    updated_at as order_last_updated_at,
    order_age_seconds as order_update_elapsed_seconds,
    is_deleted,
    source_topic,
    source_partition,
    source_offset,
    projected_at as last_projected_at
from {{ ref('stg_order_intelligence') }}

{% if is_incremental() %}
where projected_at >= (
    select coalesce(max(last_projected_at), '1900-01-01'::timestamptz)
    from {{ this }}
)
{% endif %}
