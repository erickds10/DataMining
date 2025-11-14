import os
import argparse
from sqlalchemy import create_engine, text

# -----------------------------------------
# 1. Parseo de argumentos (CLI)
# -----------------------------------------
def parse_args():
    p = argparse.ArgumentParser(description="Constructor particionado de analytics.obt_trips")
    p.add_argument("--mode", choices=["full", "append"], default="full",
                   help="full = recrea tabla; append = inserta particiones nuevas")
    p.add_argument("--year-start", type=int, required=True)
    p.add_argument("--year-end", type=int, required=True)
    p.add_argument("--services", type=str, default="yellow,green",
                   help="Lista separada por coma: yellow,green")
    p.add_argument("--run-id", type=str, default="pset4_obt")
    p.add_argument("--overwrite", type=str, default="false",
                   help="true para DROP/CREATE analytics.obt_trips en modo full")
    return p.parse_args()


# -----------------------------------------
# 2. Conexión a Postgres
# -----------------------------------------
def get_engine():
    PG_HOST   = os.getenv("PG_HOST", "postgres")
    PG_PORT   = os.getenv("PG_PORT", "5432")
    PG_DB     = os.getenv("PG_DB", "nyc_taxi")
    PG_USER   = os.getenv("PG_USER", "postgres")
    PG_PASS   = os.getenv("PG_PASSWORD", "password")
    PG_SCHEMA_ANALYTICS = os.getenv("PG_SCHEMA_ANALYTICS", "analytics")

    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    eng = create_engine(url)

    return eng, PG_SCHEMA_ANALYTICS


# -----------------------------------------
# 3. DDL de la tabla OBT
# -----------------------------------------
def ensure_obt_table(eng, schema_analytics, overwrite: bool):
    ddl_schema = f"CREATE SCHEMA IF NOT EXISTS {schema_analytics};"

    ddl_drop = f"DROP TABLE IF EXISTS {schema_analytics}.obt_trips CASCADE;"

    ddl_create = f"""
    CREATE TABLE IF NOT EXISTS {schema_analytics}.obt_trips (
        service_type          TEXT,
        pickup_datetime       TIMESTAMP WITH TIME ZONE,
        dropoff_datetime      TIMESTAMP WITH TIME ZONE,
        pickup_date           DATE,
        pickup_hour           INT,
        pickup_dow            INT,
        trip_distance_miles   DOUBLE PRECISION,
        trip_duration_min     DOUBLE PRECISION,
        avg_speed_mph         DOUBLE PRECISION,
        passenger_count       BIGINT,
        fare_amount           DOUBLE PRECISION,
        tip_amount            DOUBLE PRECISION,
        total_amount          DOUBLE PRECISION,
        tip_pct               DOUBLE PRECISION,
        pu_location_id        BIGINT,
        do_location_id        BIGINT,
        pu_borough            TEXT,
        pu_zone               TEXT,
        do_borough            TEXT,
        do_zone               TEXT,
        source_year           INT,
        source_month          INT,
        run_id                TEXT,
        built_at_utc          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    with eng.begin() as con:
        con.execute(text(ddl_schema))
        if overwrite:
            print(f"🧨 DROP TABLE {schema_analytics}.obt_trips (overwrite=true)")
            con.execute(text(ddl_drop))
        con.execute(text(ddl_create))
        print(f"✅ Tabla {schema_analytics}.obt_trips lista.")


# -----------------------------------------
# 4. Inserción particionada (año/mes)
# -----------------------------------------
def insert_partition(eng, schema_analytics, year, month, services, run_id, mode):
    schema_raw = os.getenv("PG_SCHEMA_RAW", "raw")
    svc_list = [s.strip() for s in services.split(",") if s.strip()]
    svc_in = ", ".join([f"'{s}'" for s in svc_list])

    ym_label = f"{year}-{month:02d}"
    print(f"\n➡️  Insertando partición {ym_label} (servicios={svc_list})")

    delete_sql = ""
    # En append, limpiamos sólo esa partición antes de insertar
    if mode == "append":
        delete_sql = f"""
        DELETE FROM {schema_analytics}.obt_trips
        WHERE source_year = {year} AND source_month = {month};
        """

    # SQL de inserción SOLO para ese año/mes
    sql_insert = f"""
    {delete_sql}

    INSERT INTO {schema_analytics}.obt_trips (
        service_type,
        pickup_datetime,
        dropoff_datetime,
        pickup_date,
        pickup_hour,
        pickup_dow,
        trip_distance_miles,
        trip_duration_min,
        avg_speed_mph,
        passenger_count,
        fare_amount,
        tip_amount,
        total_amount,
        tip_pct,
        pu_location_id,
        do_location_id,
        pu_borough,
        pu_zone,
        do_borough,
        do_zone,
        source_year,
        source_month,
        run_id
    )
    SELECT
        r.service_type,
        r.pickup_datetime,
        r.dropoff_datetime,
        (r.pickup_datetime AT TIME ZONE 'UTC')::date AS pickup_date,
        EXTRACT(HOUR FROM r.pickup_datetime AT TIME ZONE 'UTC')::int AS pickup_hour,
        EXTRACT(DOW  FROM r.pickup_datetime AT TIME ZONE 'UTC')::int AS pickup_dow,
        r.trip_distance                      AS trip_distance_miles,
        CASE 
            WHEN r.dropoff_datetime IS NOT NULL AND r.pickup_datetime IS NOT NULL
            THEN EXTRACT(EPOCH FROM (r.dropoff_datetime - r.pickup_datetime)) / 60.0
            ELSE NULL
        END                                   AS trip_duration_min,
        CASE 
            WHEN r.dropoff_datetime IS NOT NULL 
                 AND r.pickup_datetime IS NOT NULL
                 AND EXTRACT(EPOCH FROM (r.dropoff_datetime - r.pickup_datetime)) > 0
            THEN (r.trip_distance / (EXTRACT(EPOCH FROM (r.dropoff_datetime - r.pickup_datetime)) / 3600.0))
            ELSE NULL
        END                                   AS avg_speed_mph,
        r.passenger_count,
        r.fare_amount,
        r.tip_amount,
        r.total_amount,
        CASE 
            WHEN r.total_amount IS NOT NULL AND r.total_amount <> 0
            THEN r.tip_amount / r.total_amount
            ELSE NULL
        END                                   AS tip_pct,
        r.pu_location_id,
        r.do_location_id,
        pu.borough        AS pu_borough,
        pu.zone           AS pu_zone,
        do_.borough       AS do_borough,
        do_.zone          AS do_zone,
        r.source_year,
        r.source_month,
        '{run_id}'        AS run_id
    FROM (
        SELECT *
        FROM {schema_raw}.yellow_taxi_trip
        WHERE source_year = {year} AND source_month = {month} AND service_type = 'yellow'

        UNION ALL

        SELECT *
        FROM {schema_raw}.green_taxi_trip
        WHERE source_year = {year} AND source_month = {month} AND service_type = 'green'
    ) AS r
    LEFT JOIN {schema_raw}.taxi_zone_lookup pu
        ON pu.locationid = r.pu_location_id
    LEFT JOIN {schema_raw}.taxi_zone_lookup do_
        ON do_.locationid = r.do_location_id
    WHERE
        r.service_type IN ({svc_in});
    """

    with eng.begin() as con:
        con.execute(text(sql_insert))
    print(f"✅ Partición {ym_label} insertada en analytics.obt_trips.")


# -----------------------------------------
# 5. Main: loop por año/mes
# -----------------------------------------
def main():
    args = parse_args()
    eng, schema_analytics = get_engine()
    overwrite = str(args.overwrite).lower() == "true"

    print("➡️  Parámetros de construcción OBT:")
    print(f"    mode       = {args.mode}")
    print(f"    years      = {args.year_start}..{args.year_end}")
    print(f"    services   = {args.services}")
    print(f"    run_id     = {args.run_id}")
    print(f"    overwrite  = {overwrite}")
    print(f"    schema_raw = {os.getenv('PG_SCHEMA_RAW','raw')}")
    print(f"    schema_an  = {schema_analytics}")

    # 1) asegurar tabla OBT
    ensure_obt_table(eng, schema_analytics, overwrite)

    # 2) insertar particiones año/mes una por una
    for year in range(args.year_start, args.year_end + 1):
        for month in range(1, 13):
            insert_partition(
                eng=eng,
                schema_analytics=schema_analytics,
                year=year,
                month=month,
                services=args.services,
                run_id=args.run_id,
                mode=args.mode
            )

    print("🎉 OBT analytics.obt_trips construida (particionada por year/month).")


if __name__ == "__main__":
    main()