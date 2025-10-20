# Deber 3 Erick Daniel Suárez Veloz

# PSET 3 — NYC Taxi Analytics en Snowflake

**Curso:** Data Mining 2025-01

**Profesor:** Erick Ñauñay

---

## Índice

1. [Objetivo del PSET](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
2. [Arquitectura y diseño del pipeline](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
3. [Ambiente y herramientas](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
4. [Implementación paso a paso (con código)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
    - 4.1 [Levantamiento del ambiente](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
    - 4.2 [Conexión a Snowflake (Snowpark)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
    - 4.3 [Ingesta mensual a RAW (STG → TRIPS) con auditoría](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
    - 4.4 [Carga masiva 10 años (yellow + green)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
    - 4.5 [Creación de la OBT (One Big Table)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
    - 4.6 [Enriquecimiento (DIMs y OBT_TRIPS_ENRICHED)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
5. [Validaciones y control de calidad](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
6. [Preguntas analíticas de negocio (10 queries + gráfico + insight)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
7. [Resultados y conclusiones ejecutivas](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
8. [Entregables y formato final](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)
9. [Anexos (troubleshooting y notas)](https://www.notion.so/Deber-3-Erick-Daniel-Su-rez-Veloz-292fbe7dbe3180c08b3adbfd39228299?pvs=21)

---

## Objetivo del PSET

Construir un pipeline **reproducible y auditable** para ingestar el dataset **NYC TLC (yellow y green taxis)** en **Snowflake**, consolidarlo en una **tabla analítica final (OBT)**, enriquecerlo con **dimensiones** legibles (zonas, vendor, rate code, payment type) y responder **preguntas de negocio** con evidencias (tablas y gráficos), explicando **qué hicimos, por qué y para qué**.

**Metas específicas:**

- **RAW**: Cargar datos crudos desde Parquet (por mes y servicio) a tablas staging `STG_*` y luego a tablas finales `TRIPS_YELLOW` y `TRIPS_GREEN` via **MERGE** (idempotente).
- **AUDITORÍA**: Registrar cargas en `RAW.AUDIT_LOADS` (volumen, fuente, fecha, run_id).
- **ANALYTICS**: Crear **OBT_TRIPS** con campos derivados (duración, velocidad, tip %) y luego **OBT_TRIPS_ENRICHED** con **DIM** legibles (zonas, payment, rate, vendor).
- **ANÁLISIS**: Ejecutar 10 preguntas de negocio (SQL + visual + insight) y redactar **conclusiones**.

---

## Arquitectura y diseño del pipeline

```
Parquet (Cloudfront)
   └── (Jupyter) Descarga → User Stage @~ → COPY INTO STG_YYYYMM
        └── (RAW) MERGE STG → TRIPS_[YELLOW|GREEN] (idempotente)
             └── (RAW) AUDIT_LOADS (registro de cada carga)
                  └── (ANALYTICS) OBT_TRIPS (unión yellow/green + derivados)
                       └── (ANALYTICS) DIM_* (catálogos + taxi zones)
                            └── (ANALYTICS) OBT_TRIPS_ENRICHED (joins con DIMs)
                                 └── (ANÁLISIS) SQL + Gráficos + Insights

```

**Por qué lo armé asi:**

- **Capas (RAW vs ANALYTICS):** separan ingestión de modelado; facilitan auditoría y reproducibilidad.
- **STG → MERGE → TRIPS:** asegura **idempotencia** (si reingesto un mes, no duplico).
- **OBT (One Big Table):** formato ancho, listo para análisis sin joins costosos recurrentes.
- **DIMs:** traducen IDs a **nombres legibles** (mejoran narrativa y comprensión de negocio).
- **Auditoría:** permite rastrear **cuándo, cuánto y desde dónde** se cargó cada partición.

---

## Ambiente y herramientas

- **Docker** (contenedor con Jupyter + PySpark).

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image.png)

- **JupyterLab** (código Python + Snowpark).

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%201.png)

- **Snowflake** (Snowsight para SQL, roles/warehouses/schemas).

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%202.png)

- **Librerías**: `snowflake-connector-python`, `snowflake-snowpark-python`, `pandas`, `pyarrow`, `matplotlib`, `requests`.

---

## Implementación paso a paso (con código)

> Convención:
> 
> - **JupyterLab** = celdas **Python**
> - **Snowsight** = celdas **SQL**

### 4.1 Levantamiento del ambiente

**Objetivo:** disponer de un entorno reproducible para ejecutar notebooks y conectarse a Snowflake.

- `docker compose up -d` → levanta el contenedor `pyspark-notebook`.
- Acceso a Jupyter: `http://localhost:8888` (usar **token**).
- **Por seguridad:** no dejar contraseñas en texto plano en el notebook final (usar variables de entorno o `.env`).

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%203.png)

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%204.png)

---

### 4.2 Conexión a Snowflake (Snowpark)

**Jupyter — Celda: instalar dependencias**

```python
!pip install --quiet snowflake-connector-python snowflake-snowpark-python pyarrow pandas requests
```

**Jupyter — Celda: variables de entorno + sesión**

```python
import os
from snowflake.snowpark import Session

# ⚠️ Para el reporte: enmascara password en capturas/entrega
os.environ["SNOWFLAKE_ACCOUNT"]   = "************"
os.environ["SNOWFLAKE_USER"]      = "ERICKDS1017"
os.environ["SNOWFLAKE_PASSWORD"]  = "********"         # <- no exponer
os.environ["SNOWFLAKE_WAREHOUSE"] = "WH_DM_P3"
os.environ["SNOWFLAKE_ROLE"]      = "R_DM_P3"
os.environ["SNOWFLAKE_DATABASE"]  = "DB_TLC"
os.environ["SNOWFLAKE_SCHEMA"]    = "RAW"

conn = {k.split("SNOWFLAKE_")[1].lower(): v for k,v in os.environ.items() if k.startswith("SNOWFLAKE_")}
session = Session.builder.configs(conn).create()
session.sql("SELECT CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA()").show()
```

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%205.png)

**Snowsight — Celda: contexto y privilegios (si aplica)**

> Ejecutar con rol con permisos (ej. ACCOUNTADMIN) si fuese necesario:
> 

```sql
USE ROLE ACCOUNTADMIN;
GRANT USAGE ON WAREHOUSE WH_DM_P3 TO ROLE R_DM_P3;
GRANT USAGE ON DATABASE DB_TLC     TO ROLE R_DM_P3;
GRANT USAGE ON SCHEMA DB_TLC.RAW   TO ROLE R_DM_P3;
GRANT CREATE TABLE ON SCHEMA DB_TLC.RAW TO ROLE R_DM_P3;
GRANT CREATE STAGE ON SCHEMA DB_TLC.RAW TO ROLE R_DM_P3;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON ALL TABLES IN SCHEMA DB_TLC.RAW TO ROLE R_DM_P3;
GRANT SELECT, INSERT, UPDATE, DELETE
  ON FUTURE TABLES IN SCHEMA DB_TLC.RAW TO ROLE R_DM_P3;
```

---

### 4.3 Ingesta mensual a RAW (STG → TRIPS) con auditoría

**Motivo técnico:**

- **Descarga** Parquet del mes/servicio.
- **Subida** al **user stage** `@~` (no requiere `CREATE STAGE`).
- **COPY** con `MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE` para mapear columnas por nombre.
- **UPDATE** de metadatos (run_id, service_type, año/mes, source_path).
- **MERGE** de `STG_YYYYMM` → `TRIPS_*` (idempotencia).
- **Log** en `AUDIT_LOADS`.

**Jupyter — Celda: helpers**

```python
import os, requests, datetime as dt

def download_parquet(service, year, month):
    mm = f"{month:02d}"
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/{service}_tripdata_{year}-{mm}.parquet"
    local = f"/home/jovyan/work/{service}_{year}-{mm}.parquet"
    r = requests.get(url, stream=True, timeout=120); r.raise_for_status()
    with open(local, "wb") as f:
        for chunk in r.iter_content(1024*1024):
            if chunk: f.write(chunk)
    return local, url

def put_to_user_stage(local_path):
    return session.file.put(f"file://{local_path}", "@~", auto_compress=False, overwrite=True)

def create_stg_like(service, y, m):
    like_table = "TRIPS_YELLOW" if service=="yellow" else "TRIPS_GREEN"
    stg = f"STG_YELLOW_{y}{m:02d}" if service=="yellow" else f"STG_GREEN_{y}{m:02d}"
    session.sql(f"CREATE OR REPLACE TABLE {stg} LIKE {like_table}").collect()
    return stg

def copy_into_stg(stg, filename):
    session.sql(f"""
      COPY INTO {stg}
      FROM @~/{filename}
      FILE_FORMAT=(TYPE=PARQUET)
      MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE
      ON_ERROR=CONTINUE
    """).collect()

def update_metadata(stg, run_id, service, year, month, source_url):
    session.sql(f"""
      UPDATE {stg} SET
        run_id='{run_id}',
        service_type='{service}',
        source_year={year},
        source_month={month},
        ingested_at_utc=CURRENT_TIMESTAMP(),
        source_path='{source_url}'
    """).collect()

def count_rows(table):
    return session.sql(f"SELECT COUNT(*) c FROM {table}").collect()[0]["C"]

def insert_audit(run_id, service, year, month, rows, source_url):
    session.sql(f"""
      INSERT INTO RAW.AUDIT_LOADS
      (run_id, service_type, source_year, source_month, started_at_utc, finished_at_utc, rows_written, source_path)
      VALUES ('{run_id}','{service}',{year},{month},CURRENT_TIMESTAMP(),CURRENT_TIMESTAMP(),{rows},'{source_url}')
    """).collect()
```

**Jupyter — Celda: ejemplo Yellow 2022-01**

```python
service, year, month = "yellow", 2022, 1
run_id = f"ingesta_{service}_{year}{month:02d}_{dt.datetime.utcnow():%Y%m%d_%H%M%S}"

local, source_url = download_parquet(service, year, month)
put_to_user_stage(local)

stg = create_stg_like(service, year, month)
copy_into_stg(stg, os.path.basename(local))
update_metadata(stg, run_id, service, year, month, source_url)

rows = count_rows(stg)
insert_audit(run_id, service, year, month, rows, source_url)
rows
```

**Snowsight — Celda: MERGE a TRIPS_YELLOW**

```sql
USE ROLE R_DM_P3; USE WAREHOUSE WH_DM_P3; USE DATABASE DB_TLC; USE SCHEMA RAW;

MERGE INTO TRIPS_YELLOW AS tgt
USING STG_YELLOW_202201 AS src
ON  tgt.tpep_pickup_datetime = src.tpep_pickup_datetime
AND tgt.tpep_dropoff_datetime = src.tpep_dropoff_datetime
AND tgt.pu_location_id       = src.pu_location_id
AND tgt.do_location_id       = src.do_location_id
AND tgt.vendor_id            = src.vendor_id
WHEN MATCHED THEN UPDATE SET
    run_id=src.run_id, ingested_at_utc=src.ingested_at_utc, service_type=src.service_type,
    source_year=src.source_year, source_month=src.source_month, source_path=src.source_path,
    fare_amount=src.fare_amount, extra=src.extra, mta_tax=src.mta_tax, tip_amount=src.tip_amount,
    tolls_amount=src.tolls_amount, improvement_surcharge=src.improvement_surcharge,
    congestion_surcharge=src.congestion_surcharge, airport_fee=src.airport_fee, total_amount=src.total_amount
WHEN NOT MATCHED THEN INSERT (
    tpep_pickup_datetime, tpep_dropoff_datetime, pu_location_id, do_location_id,
    passenger_count, trip_distance, rate_code_id, store_and_fwd_flag, payment_type,
    fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge,
    congestion_surcharge, airport_fee, total_amount, vendor_id, run_id, service_type,
    source_year, source_month, ingested_at_utc, source_path
) VALUES (
    src.tpep_pickup_datetime, src.tpep_dropoff_datetime, src.pu_location_id, src.do_location_id,
    src.passenger_count, src.trip_distance, src.rate_code_id, src.store_and_fwd_flag, src.payment_type,
    src.fare_amount, src.extra, src.mta_tax, src.tip_amount, src.tolls_amount, src.improvement_surcharge,
    src.congestion_surcharge, src.airport_fee, src.total_amount, src.vendor_id, src.run_id, src.service_type,
    src.source_year, src.source_month, src.ingested_at_utc, src.source_path
);

```

*(Análogo para `TRIPS_GREEN` con campos `lpep_*` y `trip_type`)*

---

### 4.4 Carga masiva 10 años (yellow + green)

**Objetivo:** automatizar el backfill 2016–2025 (o rango indicado) para ambos servicios.

**Jupyter — Celda (loop masivo con MERGE integrado)**

```python
import datetime as dt, os

SERVICES = ["yellow", "green"]
YEARS = range(2016, 2026)  # 2016..2025 inclusive
MONTHS = range(1, 13)

def merge_sql(service, y, m):
    ym = f"{y}{m:02d}"
    if service=="yellow":
        return f"""
MERGE INTO RAW.TRIPS_YELLOW AS tgt
USING RAW.STG_YELLOW_{ym} AS src
ON  tgt.tpep_pickup_datetime = src.tpep_pickup_datetime
AND tgt.tpep_dropoff_datetime = src.tpep_dropoff_datetime
AND tgt.pu_location_id       = src.pu_location_id
AND tgt.do_location_id       = src.do_location_id
AND tgt.vendor_id            = src.vendor_id
WHEN MATCHED THEN UPDATE SET
  run_id=src.run_id, ingested_at_utc=src.ingested_at_utc, service_type=src.service_type,
  source_year=src.source_year, source_month=src.source_month, source_path=src.source_path,
  fare_amount=src.fare_amount, extra=src.extra, mta_tax=src.mta_tax, tip_amount=src.tip_amount,
  tolls_amount=src.tolls_amount, improvement_surcharge=src.improvement_surcharge,
  congestion_surcharge=src.congestion_surcharge, airport_fee=src.airport_fee, total_amount=src.total_amount
WHEN NOT MATCHED THEN INSERT (
  tpep_pickup_datetime, tpep_dropoff_datetime, pu_location_id, do_location_id,
  passenger_count, trip_distance, rate_code_id, store_and_fwd_flag, payment_type,
  fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge,
  congestion_surcharge, airport_fee, total_amount, vendor_id, run_id, service_type,
  source_year, source_month, ingested_at_utc, source_path
) VALUES (
  src.tpep_pickup_datetime, src.tpep_dropoff_datetime, src.pu_location_id, src.do_location_id,
  src.passenger_count, src.trip_distance, src.rate_code_id, src.store_and_fwd_flag, src.payment_type,
  src.fare_amount, src.extra, src.mta_tax, src.tip_amount, src.tolls_amount, src.improvement_surcharge,
  src.congestion_surcharge, src.airport_fee, src.total_amount, src.vendor_id, src.run_id, src.service_type,
  src.source_year, src.source_month, src.ingested_at_utc, src.source_path
);"""
    else:
        return f"""
MERGE INTO RAW.TRIPS_GREEN AS tgt
USING RAW.STG_GREEN_{ym} AS src
ON  tgt.lpep_pickup_datetime = src.lpep_pickup_datetime
AND tgt.lpep_dropoff_datetime = src.lpep_dropoff_datetime
AND tgt.pu_location_id       = src.pu_location_id
AND tgt.do_location_id       = src.do_location_id
AND tgt.vendor_id            = src.vendor_id
WHEN MATCHED THEN UPDATE SET
  run_id=src.run_id, ingested_at_utc=src.ingested_at_utc, service_type=src.service_type,
  source_year=src.source_year, source_month=src.source_month, source_path=src.source_path,
  trip_type=src.trip_type,
  fare_amount=src.fare_amount, extra=src.extra, mta_tax=src.mta_tax, tip_amount=src.tip_amount,
  tolls_amount=src.tolls_amount, improvement_surcharge=src.improvement_surcharge,
  congestion_surcharge=src.congestion_surcharge, total_amount=src.total_amount
WHEN NOT MATCHED THEN INSERT (
  lpep_pickup_datetime, lpep_dropoff_datetime, pu_location_id, do_location_id,
  passenger_count, trip_distance, rate_code_id, store_and_fwd_flag, payment_type,
  fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge,
  congestion_surcharge, total_amount, trip_type, vendor_id, run_id, service_type,
  source_year, source_month, ingested_at_utc, source_path
) VALUES (
  src.lpep_pickup_datetime, src.lpep_dropoff_datetime, src.pu_location_id, src.do_location_id,
  src.passenger_count, src.trip_distance, src.rate_code_id, src.store_and_fwd_flag, src.payment_type,
  src.fare_amount, src.extra, src.mta_tax, src.tip_amount, src.tolls_amount, src.improvement_surcharge,
  src.congestion_surcharge, src.total_amount, src.trip_type, src.vendor_id, src.run_id, src.service_type,
  src.source_year, src.source_month, src.ingested_at_utc, src.source_path
);"""

for svc in SERVICES:
    for y in YEARS:
        for m in MONTHS:
            try:
                mm = f"{m:02d}"
                local, url = download_parquet(svc, y, m)
                put_to_user_stage(local)
                stg = create_stg_like(svc, y, m)
                copy_into_stg(stg, os.path.basename(local))
                run_id = f"backfill_{svc}_{y}{mm}"
                update_metadata(stg, run_id, svc, y, m, url)
                rows = count_rows(stg)
                insert_audit(run_id, svc, y, m, rows, url)
                session.sql(merge_sql(svc, y, m)).collect()
                print(f"✅ {svc} {y}-{mm}: {rows} filas → MERGE OK")
            except Exception as e:
                print(f"❌ {svc} {y}-{mm}: {e}")
```

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%206.png)

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%207.png)

---

### 4.5 Creación de la One Big Table u OBT

**Motivo:** unificar yellow+green en una sola tabla **listo-para-analizar** con campos derivados.

**Snowsight — Celda: OBT_TRIPS**

```sql
USE ROLE R_DM_P3; USE WAREHOUSE WH_DM_P3; USE DATABASE DB_TLC; USE SCHEMA ANALYTICS;

CREATE OR REPLACE TABLE OBT_TRIPS AS
SELECT
  'yellow' AS service_type,
  tpep_pickup_datetime  AS pickup_datetime,
  tpep_dropoff_datetime AS dropoff_datetime,
  pu_location_id, do_location_id,
  passenger_count, trip_distance, rate_code_id, store_and_fwd_flag, payment_type,
  fare_amount, extra, mta_tax, tip_amount, tolls_amount,
  improvement_surcharge, congestion_surcharge, airport_fee, total_amount,
  vendor_id, run_id, source_year, source_month, ingested_at_utc, source_path,
  CAST(DATEDIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime)/60.0 AS FLOAT) AS trip_duration_min,
  IFF(DATEDIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime)>0,
      trip_distance / (DATEDIFF('second', tpep_pickup_datetime, tpep_dropoff_datetime)/3600.0), NULL) AS avg_speed_mph,
  IFF(total_amount>0, tip_amount/total_amount, 0) AS tip_pct,
  YEAR(tpep_pickup_datetime) AS year, MONTH(tpep_pickup_datetime) AS month,
  DAYOFWEEKISO(tpep_pickup_datetime) AS dow
FROM RAW.TRIPS_YELLOW
UNION ALL
SELECT
  'green',
  lpep_pickup_datetime, lpep_dropoff_datetime,
  pu_location_id, do_location_id,
  passenger_count, trip_distance, rate_code_id, store_and_fwd_flag, payment_type,
  fare_amount, extra, mta_tax, tip_amount, tolls_amount,
  improvement_surcharge, congestion_surcharge, NULL::FLOAT AS airport_fee, total_amount,
  vendor_id, run_id, source_year, source_month, ingested_at_utc, source_path,
  CAST(DATEDIFF('second', lpep_pickup_datetime, lpep_dropoff_datetime)/60.0 AS FLOAT),
  IFF(DATEDIFF('second', lpep_pickup_datetime, lpep_dropoff_datetime)>0,
      trip_distance / (DATEDIFF('second', lpep_pickup_datetime, lpep_dropoff_datetime)/3600.0), NULL),
  IFF(total_amount>0, tip_amount/total_amount, 0),
  YEAR(lpep_pickup_datetime), MONTH(lpep_pickup_datetime), DAYOFWEEKISO(lpep_pickup_datetime)
FROM RAW.TRIPS_GREEN;

SELECT COUNT(*) FROM OBT_TRIPS;
```

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%208.png)

---

### 4.6 Enriquecimiento (DIMs y OBT_TRIPS_ENRICHED)

**Snowsight — Celda: DIMs**

```sql
-- Payment Type
CREATE OR REPLACE TABLE ANALYTICS.DIM_PAYMENT_TYPE (
  payment_type_id INTEGER PRIMARY KEY, payment_type_name STRING
);
INSERT OVERWRITE INTO ANALYTICS.DIM_PAYMENT_TYPE VALUES
(1,'Credit Card'),(2,'Cash'),(3,'No Charge'),(4,'Dispute'),(5,'Unknown'),(6,'Voided Trip');

-- Rate Code
CREATE OR REPLACE TABLE ANALYTICS.DIM_RATE_CODE (
  rate_code_id INTEGER PRIMARY KEY, rate_code_desc STRING
);
INSERT OVERWRITE INTO ANALYTICS.DIM_RATE_CODE VALUES
(1,'Standard rate'),(2,'JFK'),(3,'Newark'),(4,'Nassau or Westchester'),(5,'Negotiated fare'),(6,'Group ride');

-- Vendor
CREATE OR REPLACE TABLE ANALYTICS.DIM_VENDOR (
  vendor_id INTEGER PRIMARY KEY, vendor_name STRING
);
INSERT OVERWRITE INTO ANALYTICS.DIM_VENDOR VALUES (1,'CMT'),(2,'VeriFone');
```

**Snowsight — Celda: DIM_TAXI_ZONES**

*(Carga `taxi_zone_lookup.csv` a tu **user stage** `@~` desde Snowsight UI → Data → Stages → User Stage → Upload)*

```sql
USE SCHEMA ANALYTICS;

CREATE OR REPLACE TABLE DIM_TAXI_ZONES (
  location_id INTEGER, borough STRING, zone STRING, service_zone STRING
);

COPY INTO DIM_TAXI_ZONES
FROM @~/taxi_zone_lookup.csv
FILE_FORMAT=(TYPE=CSV FIELD_OPTIONALLY_ENCLOSED_BY='"' SKIP_HEADER=1)
ON_ERROR=CONTINUE;

SELECT COUNT(*) FROM DIM_TAXI_ZONES;
```

**Snowsight — Celda: OBT_TRIPS_ENRICHED**

```sql
CREATE OR REPLACE TABLE OBT_TRIPS_ENRICHED AS
SELECT
  t.service_type, t.pickup_datetime, t.dropoff_datetime,
  t.pu_location_id, t.do_location_id, t.rate_code_id, t.payment_type, t.vendor_id,
  zpu.borough AS pickup_borough, zpu.zone AS pickup_zone, zpu.service_zone AS pickup_service_zone,
  zdo.borough AS dropoff_borough, zdo.zone AS dropoff_zone, zdo.service_zone AS dropoff_service_zone,
  rc.rate_code_desc, pt.payment_type_name, vd.vendor_name,
  t.passenger_count, t.trip_distance, t.fare_amount, t.extra, t.mta_tax, t.tip_amount, t.tolls_amount,
  t.improvement_surcharge, t.congestion_surcharge, t.airport_fee, t.total_amount,
  t.trip_duration_min, t.avg_speed_mph, t.tip_pct,
  t.year, t.month, t.dow, t.run_id, t.source_year, t.source_month, t.ingested_at_utc, t.source_path
FROM OBT_TRIPS t
LEFT JOIN DIM_TAXI_ZONES   zpu ON t.pu_location_id=zpu.location_id
LEFT JOIN DIM_TAXI_ZONES   zdo ON t.do_location_id=zdo.location_id
LEFT JOIN DIM_RATE_CODE    rc  ON t.rate_code_id=rc.rate_code_id
LEFT JOIN DIM_PAYMENT_TYPE pt  ON t.payment_type=pt.payment_type_id
LEFT JOIN DIM_VENDOR       vd  ON t.vendor_id=vd.vendor_id;

SELECT COUNT(*) FROM OBT_TRIPS_ENRICHED;
```

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%209.png)

---

## Validaciones y control de calidad

**Checks:**

- **Conteos** entre `STG_*` y `TRIPS_*` por mes (no duplicados).
- **AUDIT_LOADS**: sumas por mes coinciden con conteos en `STG_*`.
- **OBT vs TRIPS**: `COUNT(*)` esperado tras unión yellow+green.
- **DIM joins**: spot-check de borough/zone no nulos para IDs frecuentes.

**Snowsight — Ejemplos:**

```sql
SELECT service_type, source_year, source_month, SUM(rows_written)
FROM RAW.AUDIT_LOADS
GROUP BY 1,2,3 ORDER BY 2,3,1;

SELECT 'Y' svc, COUNT(*) c FROM RAW.TRIPS_YELLOW
UNION ALL
SELECT 'G', COUNT(*) FROM RAW.TRIPS_GREEN;

SELECT COUNT(*) FROM ANALYTICS.OBT_TRIPS;
SELECT COUNT(*) FROM ANALYTICS.OBT_TRIPS_ENRICHED;
```

![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2010.png)

---

## Preguntas analíticas de negocio (10 queries + gráfico + insight)

> A continuación listamos las 10 preguntas ejecutadas en Jupyter sobre ANALYTICS.OBT_TRIPS_ENRICHED, con el SQL, tabla/gráfico y la interpretación.
> 
> 
> (En el notebook incluimos las funciones `run_sql`, `show_table`, `bar_from_df`, `line_from_df`.)
> 
> > Nota previa
> > 
> > - Todas las consultas usan **`DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED`**.
> > - Si tu enriquecida aún no tiene boroughs (o prefieres ir a la base), cambia el `FROM` por `DB_TLC.ANALYTICS.OBT_TRIPS` y **agrega un join** a `ANALYTICS.DIM_TAXI_ZONES` usando `pu_location_id`/`do_location_id`.
> > - Fechas: acoto a **2016–2025** y **recalculo el año con `YEAR(pickup_datetime)`** (evita problemas de la columna `year`).
> 
> ---
> 
> ## Pregunta 1 — Propina promedio por método de pago
> 
> **SQL**
> 
> ```sql
> SELECT
>   payment_type_name,
>   ROUND(AVG(tip_pct) * 100, 2) AS avg_tip_pct,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY payment_type_name
> ORDER BY avg_tip_pct DESC;
> 
> ```
> 
> **Análisis breve**
> 
> Los pagos **con tarjeta** suelen mostrar mayor % de propina que **efectivo**. Esto sugiere que los métodos electrónicos (UX + sugerencias de tip) impulsan propinas más altas.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2011.png)
> 
> ---
> 
> ## Pregunta 2 — Velocidad promedio por borough de origen
> 
> **SQL**
> 
> ```sql
> SELECT
>   COALESCE(pickup_borough, 'UNKNOWN') AS pickup_borough,
>   ROUND(AVG(IFF(avg_speed_mph BETWEEN 1 AND 60, avg_speed_mph, NULL)), 2) AS avg_speed_mph,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY pickup_borough
> ORDER BY avg_speed_mph DESC;
> 
> ```
> 
> **Análisis breve**
> 
> Boroughs periféricos tienden a velocidades mayores por menor congestión, mientras **Manhattan** suele ser el más lento.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2012.png)
> 
> ---
> 
> ## Pregunta 3 — Tendencia de viajes por año y servicio
> 
> **SQL**
> 
> ```sql
> SELECT
>   YEAR(pickup_datetime) AS cal_year,
>   service_type,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY cal_year, service_type
> ORDER BY cal_year, service_type;
> ```
> 
> **Análisis breve**
> 
> Se visualiza la evolución anual de **yellow** vs **green**. Usualmente **yellow** domina el volumen, con caídas en años de disrupción (pandemia) y recuperación posterior.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2013.png)
> 
> ---
> 
> ## Pregunta 4 — Ticket promedio por año y servicio (optimizada)
> 
> **SQL**
> 
> ```sql
> SELECT
>   YEAR(pickup_datetime) AS cal_year,
>   service_type,
>   ROUND(AVG(IFF(total_amount BETWEEN 0 AND 1000, total_amount, NULL)), 2) AS avg_ticket,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY cal_year, service_type
> ORDER BY cal_year, service_type;
> 
> ```
> 
> **Análisis breve**
> 
> El **ticket promedio** de **yellow** suele ser mayor al de **green** (trayectos más largos y zonas céntricas).
> 
> ---
> 
> ## Pregunta 5 — Top 10 zonas de destino
> 
> **SQL**
> 
> ```sql
> SELECT
>   COALESCE(dropoff_zone, 'UNKNOWN') AS dropoff_zone,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY dropoff_zone
> ORDER BY trips DESC
> LIMIT 10;
> 
> ```
> 
> **Análisis breve**
> 
> Útil para **planificación de flota** y puntos de mayor demanda.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2014.png)
> 
> ---
> 
> ## Pregunta 6 — Propina promedio por año y método de pago
> 
> **SQL**
> 
> ```sql
> SELECT
>   YEAR(pickup_datetime) AS cal_year,
>   payment_type_name,
>   ROUND(AVG(tip_pct) * 100, 2) AS avg_tip_pct,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY cal_year, payment_type_name
> ORDER BY cal_year, avg_tip_pct DESC;
> 
> ```
> 
> **Análisis breve**
> 
> La ventaja de **tarjeta** en propinas se mantiene por año.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2015.png)
> 
> ---
> 
> ## Pregunta 7 — Mix anual por borough de origen (participación %)
> 
> **SQL**
> 
> ```sql
> WITH base AS (
>   SELECT YEAR(pickup_datetime) AS cal_year,
>          COALESCE(pickup_borough, 'UNKNOWN') AS pickup_borough
>   FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
>   WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> )
> SELECT
>   cal_year,
>   pickup_borough,
>   COUNT(*) AS trips,
>   ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY cal_year), 2) AS pct_year
> FROM base
> GROUP BY cal_year, pickup_borough
> ORDER BY cal_year, trips DESC;
> 
> ```
> 
> **Análisis breve**
> 
> Seguir el **% por borough** muestra desplazamientos de demanda hacia/desde zonas periféricas.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2016.png)
> 
> ---
> 
> ## Pregunta 8 — Distribución por Rate Code
> 
> **SQL**
> 
> ```sql
> SELECT
>   rate_code_desc,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY rate_code_desc
> ORDER BY trips DESC;
> ```
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2017.png)
> 
> ---
> 
> ## Pregunta 9 — Ingreso total por año y servicio
> 
> **SQL**
> 
> ```sql
> SELECT
>   YEAR(pickup_datetime) AS cal_year,
>   service_type,
>   ROUND(SUM(IFF(total_amount BETWEEN -50 AND 2000, total_amount, NULL)), 2) AS revenue
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY cal_year, service_type
> ORDER BY cal_year, service_type;
> 
> ```
> 
> **Análisis breve**
> 
> El **revenue** suele estar dominado por **yellow**. Valora la recuperación pos-2020 y cambios en **mix**/tarifas. Útil para decisiones de **capacidad** y **pricing**.
> 
> ![image.png](Deber%203%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%20292fbe7dbe3180c08b3adbfd39228299/image%2018.png)
> 
> ---
> 
> ## Pregunta 10 — Duración promedio por año y borough (optimizada)
> 
> **SQL**
> 
> ```sql
> SELECT
>   YEAR(pickup_datetime) AS cal_year,
>   COALESCE(pickup_borough, 'UNKNOWN') AS pickup_borough,
>   ROUND(AVG(IFF(trip_duration_min BETWEEN 1 AND 180
>                 AND trip_distance BETWEEN 0 AND 100,  -- defensivo
>                 trip_duration_min, NULL)), 2) AS avg_duration_min,
>   COUNT(*) AS trips
> FROM DB_TLC.ANALYTICS.OBT_TRIPS_ENRICHED
> WHERE pickup_datetime BETWEEN '2016-01-01' AND '2025-12-31 23:59:59'
> GROUP BY cal_year, pickup_borough
> ORDER BY cal_year, pickup_borough;
> 
> ```
> 
> **Análisis breve**
> 
> Las **duraciones** tienden a ser **más altas** en boroughs extensos o con menor densidad de destinos; **Manhattan** muestra duraciones más bajas por trayectos cortos.
> 

---

## Resultados y conclusiones ejecutivas

**Hallazgos clave (ejemplo, ajústalo a tus resultados):**

- **Demanda:** tendencia decreciente en `yellow` desde 2017; `green` más estable en barrios periféricos.
- **Propinas:** pagos con **tarjeta** muestran mayor `tip_pct` que efectivo.
- **Ticket promedio:** `yellow` > `green` por concentrarse en zonas céntricas y trayectos más largos.
- **Velocidad:** mayor en **Queens/Staten Island** (menos congestión) vs **Manhattan**.
- **Zonas top:** `Midtown`, `LaGuardia` y `JFK` entre los destinos más frecuentes.

**Implicaciones de negocio:**

- Promover métodos de pago electrónicos para incentivar propinas.
- Optimizar flotas y precios en zonas/horarios de mayor demanda.
- Ajustar tiempos estimados y rutas en barrios con congestión.

---

## Anexos (troubleshooting y notas)

- **Token expirado (Snowflake):**
    
    Regenerar sesión Snowpark:
    
    ```python
    import pandas as pd
    
    def _new_session():
        """Recrea la sesión usando las mismas env vars."""
        global session
        try:
            session.close()
        except:
            pass
        from snowflake.snowpark import Session
        cfg = {
          "account":   os.getenv("SNOWFLAKE_ACCOUNT"),
          "user":      os.getenv("SNOWFLAKE_USER"),
          "password":  os.getenv("SNOWFLAKE_PASSWORD"),
          "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
          "role":      os.getenv("SNOWFLAKE_ROLE"),
          "database":  os.getenv("SNOWFLAKE_DATABASE"),
          "schema":    os.getenv("SNOWFLAKE_SCHEMA"),
        }
        session = Session.builder.configs(cfg).create()
        # fija contexto por si acaso
        session.sql("USE ROLE {}".format(cfg["role"])).collect()
        session.sql("USE WAREHOUSE {}".format(cfg["warehouse"])).collect()
        session.sql("USE DATABASE {}".format(cfg["database"])).collect()
        session.sql("USE SCHEMA {}".format(cfg["schema"])).collect()
        return session
    
    def run_sql(sql: str) -> pd.DataFrame:
        """Ejecuta SQL y si el token expiró, recrea sesión y reintenta 1 vez."""
        try:
            return session.sql(sql).to_pandas()
        except Exception as e:
            msg = str(e)
            # Códigos típicos: 390114/08001
            if "Authentication token has expired" in msg or "390114" in msg:
                _new_session()
                return session.sql(sql).to_pandas()
            raise
    
    ```
    
- **Privilegios insuficientes:**
    
    Asegurar GRANTs en `DB_TLC.RAW` (USAGE, CREATE TABLE/STAGE, SELECT/INSERT/UPDATE/DELETE), y en `DB_TLC.ANALYTICS` para crear OBT y DIMs.
    
- **COPY Parquet ‘one VARIANT column’ error:**
    
    Usar `MATCH_BY_COLUMN_NAME=CASE_INSENSITIVE` en `COPY INTO` para mapear columnas por nombre.
    
- **Buenas prácticas de seguridad:**
    
    No exponer **passwords** en el notebook final; usar variables de entorno o secretos de Snowflake. En el PDF, **enmascara** credenciales en capturas.