with base as (
  {{ union_raw_trips() }}
)
select
  vendor_id,
  cast(pickup_datetime  as timestamp_ntz) as pickup_datetime,
  cast(dropoff_datetime as timestamp_ntz) as dropoff_datetime,
  pickup_location_id,
  dropoff_location_id,
  passenger_count,
  trip_distance,
  total_amount,
  payment_type,
  service_type,
  to_date(pickup_datetime) as pickup_date
from base
where pickup_datetime is not null
  and dropoff_datetime is not null
