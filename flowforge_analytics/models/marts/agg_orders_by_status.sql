select
    order_status,
    currency,
    count(*) as order_count,
    sum(order_value) as total_order_value,
    avg(order_value) as average_order_value,
    min(order_created_at) as first_order_created_at,
    max(order_created_at) as latest_order_created_at
from {{ ref('fct_orders') }}
where is_deleted = false
group by
    order_status,
    currency
