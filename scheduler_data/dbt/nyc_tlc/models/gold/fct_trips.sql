{{ config(
    cluster_by = ['pickup_date','service_type','pickup_location_id'],
    tags = ['gold','fact']
) }}
select
  t.pickup_date,
  t.service_type,
  t.vendor_id,
  t.pickup_location_id,
  t.dropoff_location_id,
  t.passenger_count,
  t.trip_distance,
  t.total_amount,
  t.payment_type
from {{ ref('trips_cleaned') }} t
