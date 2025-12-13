select
  cast(LOCATIONID as number) as zone_id,
  coalesce(BOROUGH, '')      as borough,
  coalesce(ZONE, '')         as zone,
  coalesce(SERVICE_ZONE, '') as service_zone
from {{ target.database }}.RAW.TAXI_ZONE_LOOKUP_NORM
group by 1,2,3,4
