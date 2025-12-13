{{ config(
    materialized='table',
    schema='RAW', 
) }}
SELECT
  "LocationID"::NUMBER        AS LOCATIONID,
  "Borough"::STRING           AS BOROUGH,
  "Zone"::STRING              AS ZONE,
  "SERVICE_ZONE"::STRING      AS SERVICE_ZONE
FROM {{ source('raw', 'TAXI_ZONE_LOOKUP') }}
UNION ALL
SELECT
  "LocationID"::NUMBER,
  "Borough"::STRING,
  "Zone"::STRING,
  "SERVICE_ZONE"::STRING
FROM {{ ref('taxi_zone_lookup') }} 
