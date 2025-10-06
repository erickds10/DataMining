{% macro union_raw_trips() %}
{% if not execute %}
  select
    cast(null as number)        as vendor_id,
    cast(null as timestamp_ntz) as pickup_datetime,
    cast(null as timestamp_ntz) as dropoff_datetime,
    cast(null as number)        as pickup_location_id,
    cast(null as number)        as dropoff_location_id,
    cast(null as number)        as passenger_count,
    cast(null as float)         as trip_distance,
    cast(null as float)         as total_amount,
    cast(null as number)        as payment_type,
    cast(null as string)        as service_type
  where 1=0
{% else %}

  -- SOLO tablas que realmente existen en RAW
  {% set q_is %}
    select table_name
    from {{ target.database }}.information_schema.tables
    where table_schema = 'RAW'
      and regexp_like(table_name, '^TLC_(YELLOW|GREEN)_TRIPS_[0-9]{4}_[0-9]{2}$')
    order by table_name
  {% endset %}

  {% set res = run_query(q_is) %}
  {% set names = (res.columns[0].values() if res is not none else []) %}

  {% if names | length == 0 %}
    {% do exceptions.raise_compiler_error("No hay tablas TLC_*_TRIPS_YYYY_MM en RAW.") %}
  {% endif %}

  {% set selects = [] %}
  {% for t in names %}
    {% set svc = 'yellow' if 'YELLOW' in t else 'green' %}
    {% if svc == 'yellow' %}
      {% set pickup  = 'tpep_pickup_datetime'  %}
      {% set dropoff = 'tpep_dropoff_datetime' %}
    {% else %}
      {% set pickup  = 'lpep_pickup_datetime'  %}
      {% set dropoff = 'lpep_dropoff_datetime' %}
    {% endif %}
    {% set fqn = adapter.quote(target.database) ~ '.RAW.' ~ adapter.quote(t) %}

    {% set sel %}
      select
        TRY_TO_NUMBER(TO_VARCHAR("VendorID"))      as vendor_id,
        cast({{ pickup }}  as timestamp_ntz)       as pickup_datetime,
        cast({{ dropoff }} as timestamp_ntz)       as dropoff_datetime,
        TRY_TO_NUMBER(TO_VARCHAR("PULocationID"))  as pickup_location_id,
        TRY_TO_NUMBER(TO_VARCHAR("DOLocationID"))  as dropoff_location_id,
        TRY_TO_NUMBER(TO_VARCHAR(passenger_count)) as passenger_count,
        TRY_TO_DOUBLE(TO_VARCHAR(trip_distance))   as trip_distance,
        TRY_TO_DOUBLE(TO_VARCHAR(total_amount))    as total_amount,
        TRY_TO_NUMBER(TO_VARCHAR(payment_type))    as payment_type,
        '{{ svc }}'::string                        as service_type
      from {{ fqn }}
    {% endset %}
    {% do selects.append(sel) %}
  {% endfor %}

  {{ selects | join('\nUNION ALL\n') }}
{% endif %}
{% endmacro %}
