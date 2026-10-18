-- Report stale, missing, extra, or value-mismatched order projections. A five
-- minute grace period accounts for the asynchronous Kafka/Spark pipeline.
with operational as (
    select
        id,
        order_number,
        customer_id,
        status,
        currency,
        subtotal,
        tax_amount,
        shipping_amount,
        discount_amount,
        total_amount,
        created_at,
        updated_at
    from {{ source('flowforge_operational', 'orders') }}
),
projected as (
    select *
    from {{ source('flowforge_analytics', 'order_state') }}
)
select
    operational.id as operational_order_id,
    projected.order_id as projected_order_id
from operational
full outer join projected
    on operational.id = projected.order_id
where
    (
        operational.id is null
        and projected.is_deleted = false
    )
    or (
        projected.order_id is null
        and operational.updated_at < now() - interval '5 minutes'
    )
    or (
        operational.id is not null
        and projected.order_id is not null
        and operational.updated_at < now() - interval '5 minutes'
        and (
            projected.is_deleted = true
            or operational.order_number is distinct from projected.order_number
            or operational.customer_id is distinct from projected.customer_id
            or operational.status is distinct from projected.status
            or operational.currency is distinct from projected.currency
            or operational.subtotal is distinct from projected.subtotal
            or operational.tax_amount is distinct from projected.tax_amount
            or operational.shipping_amount is distinct from projected.shipping_amount
            or operational.discount_amount is distinct from projected.discount_amount
            or operational.total_amount is distinct from projected.total_amount
            or operational.created_at is distinct from projected.created_at
            or operational.updated_at is distinct from projected.updated_at
        )
    )
