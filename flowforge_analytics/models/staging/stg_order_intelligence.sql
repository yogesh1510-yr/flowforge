select
    order_id,
    order_number,
    customer_id,
    lower(status) as status,
    currency,
    subtotal,
    tax_amount,
    shipping_amount,
    discount_amount,
    total_amount,
    created_at,
    updated_at,
    order_age_seconds,
    source_topic,
    source_partition,
    source_offset,
    projected_at
from {{ source('flowforge_analytics', 'order_intelligence_test') }}