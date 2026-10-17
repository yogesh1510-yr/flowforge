{% snapshot orders_snapshot %}

{{
    config(
        target_schema='flowforge_snapshots',
        unique_key='order_id',
        strategy='timestamp',
        updated_at='updated_at'
    )
}}

select
    order_id,
    order_number,
    customer_id,
    status,
    currency,
    total_amount,
    created_at,
    updated_at
from {{ source('flowforge_analytics', 'order_intelligence_test') }}

{% endsnapshot %}