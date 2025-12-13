# Deber 2 “Proyecto 02 — NYC TLC Analytics Engineering (Mage + Snowflake + dbt)”

> Objetivo
> 
> 
> Ingestar Parquet 2015–2025 (Yellow/Green) → **RAW** (Snowflake), estandarizar/enriquecer en **SILVER**, construir **GOLD** (estrella: hechos + dimensiones), **clustering** de la tabla de hechos, y responder **5 preguntas de negocio** sobre GOLD.
> 

---

## 0) Resumen de arquitectura

- **Orquestación:** Mage
- **Raw/Bronze:** Tablas por mes y servicio (p. ej. `RAW.TLC_YELLOW_TRIPS_2021_01`)
- **Silver:** `SILVER.TRIPS_CLEANED` (tipificación, limpieza, enriquecimiento mínimo)
- **Gold:**
    - Hechos: `GOLD.FCT_TRIPS`
    - Dimensiones: `GOLD.DIM_ZONE`
- **Clustering:** en `GOLD.FCT_TRIPS` (ver sección 8)
- **Calidad:** tests dbt (not_null, unique, accepted_values, relaciones)
- **Auditoría:** `RAW.LOAD_AUDIT`

![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image.png)

---

## 1) Matriz de cobertura (2015–2025)

> RAW (SHOW TABLES IN SCHEMA DB_TLC.RAW)
> 

> 
> 
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%201.png)
> 

---

## 2) Seguridad y operación

### 2.1 Secrets (Mage)

- `SNOWFLAKE_ACCOUNT` = `{{emc22675.us-east-1}}`
- `SNOWFLAKE_USER` = `SVC_TLC_MAGE`
- `SNOWFLAKE_PASSWORD` = `{{******}}`
- `SNOWFLAKE_ROLE` = `R_DP_TLC_MAGE`
- `SNOWFLAKE_WAREHOUSE` = `COMPUTE_WH`
- `SNOWFLAKE_DATABASE` = `DB_TLC`
- `SNOWFLAKE_SCHEMA_RAW` = `RAW`

> 
> 
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%202.png)
> 

### 2.2 Rol y mínimos privilegios (ejecuta como `ACCOUNTADMIN`)

```sql
-- Rol operativo
CREATE ROLE IF NOT EXISTS R_DP_TLC_MAGE;

-- Accesos mínimos
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE R_DP_TLC_MAGE;

GRANT USAGE ON DATABASE DB_TLC TO ROLE R_DP_TLC_MAGE;
GRANT USAGE ON SCHEMA DB_TLC.RAW    TO ROLE R_DP_TLC_MAGE;
GRANT USAGE ON SCHEMA DB_TLC.SILVER TO ROLE R_DP_TLC_MAGE;
GRANT USAGE ON SCHEMA DB_TLC.GOLD   TO ROLE R_DP_TLC_MAGE;

GRANT CREATE TABLE ON SCHEMA DB_TLC.RAW    TO ROLE R_DP_TLC_MAGE;
GRANT CREATE TABLE ON SCHEMA DB_TLC.SILVER TO ROLE R_DP_TLC_MAGE;
GRANT CREATE TABLE ON SCHEMA DB_TLC.GOLD   TO ROLE R_DP_TLC_MAGE;
GRANT CREATE VIEW  ON SCHEMA DB_TLC.SILVER TO ROLE R_DP_TLC_MAGE;

-- Usuario de servicio
USE ROLE USERADMIN;
CREATE USER IF NOT EXISTS SVC_TLC_MAGE
  LOGIN_NAME           = SVC_TLC_MAGE
  DEFAULT_ROLE         = R_DP_TLC_MAGE
  DEFAULT_WAREHOUSE    = COMPUTE_WH
  DEFAULT_NAMESPACE    = DB_TLC.RAW
  MUST_CHANGE_PASSWORD = FALSE
  PASSWORD             = '{{SET_PASSWORD}}';

USE ROLE SECURITYADMIN;
GRANT ROLE R_DP_TLC_MAGE TO USER SVC_TLC_MAGE;

```

> Comprobación:
> 

```sql
USE ROLE R_DP_TLC_MAGE;
USE WAREHOUSE COMPUTE_WH;
USE DATABASE DB_TLC;
USE SCHEMA RAW;

SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();
```

> 
> 
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%203.png)
> 

---

## 3) Ingesta (Mage) a RAW + auditoría

### 3.1 Loader (descarga Parquet)

En tu **block de loader** (Python en Mage) usa el manifest (service/year/month/url) y el exporter por chunks.

> Ejecuta para probar 1 mes:
> 
- Variables del pipeline:
    
    `services = ["yellow"]`
    
    `years = [2021]`
    
    `months = [1]`
    
    `batch_rows = 250000`
    

### 3.2 Exporter con “heartbeat” + auditoría (`RAW.LOAD_AUDIT`)

> Crea la tabla de auditoría (si no existe):
> 

```sql
CREATE TABLE IF NOT EXISTS DB_TLC.RAW.LOAD_AUDIT(
  RUN_TS_UTC   TIMESTAMP_NTZ,
  SERVICE_TYPE STRING,
  YEAR         NUMBER,
  MONTH        NUMBER,
  SOURCE_URL   STRING,
  TARGET_TABLE STRING,
  ROWS_LOADED  NUMBER,
  CHUNKS       NUMBER,
  STATUS       STRING,
  ERROR_MSG    STRING,
  ELAPSED_SEC  NUMBER
);

```

> Monitoreo (ejemplo de consulta):
> 

```sql
SELECT YEAR, MONTH, SERVICE_TYPE,
       COUNT(*) AS loads,
       SUM(CASE WHEN STATUS='OK' THEN 1 ELSE 0 END) AS OK_runs,
       SUM(ROWS_LOADED) AS rows_total
FROM DB_TLC.RAW.LOAD_AUDIT
GROUP BY 1,2,3
ORDER BY 1,2,3;

```

> 
> 
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%204.png)
> 

---

## 4) Normalización de Taxi Zones (RAW helper)

> Solo si no tienes seed en dbt: crea una tabla normalizada (uso en GOLD.dim_zone):
> 

```sql
CREATE OR REPLACE TABLE DB_TLC.RAW.TAXI_ZONE_LOOKUP_NORM AS
SELECT
  "LocationID"::NUMBER       AS LOCATIONID,
  "Borough"::STRING          AS BOROUGH,
  "Zone"::STRING             AS ZONE,
  "service_zone"::STRING     AS SERVICE_ZONE
FROM DB_TLC.RAW.TAXI_ZONE_LOOKUP;

DESC TABLE DB_TLC.RAW.TAXI_ZONE_LOOKUP_NORM;
```

> SELECT * FROM DB_TLC.RAW.TAXI_ZONE_LOOKUP_NORM LIMIT 10;
> 

![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%205.png)

---

## 5) dbt — instalación, perfiles y proyecto

### 5.1 Entorno (dentro del contenedor de Mage)

```bash
# (recomendado) venv dedicado a dbt
python -m venv /home/src/.venvs/dbt
source /home/src/.venvs/dbt/bin/activate
pip install --upgrade pip
pip install dbt-snowflake==1.8.4
```

### 5.2 Variables de entorno (para profiles)

```bash
# /home/src/dbt/env.dbt
export SNOWFLAKE_ACCOUNT="emc22675.us-east-1"
export SNOWFLAKE_USER="SVC_TLC_MAGE"
export SNOWFLAKE_PASSWORD="{{******}}"
export SNOWFLAKE_ROLE="R_DP_TLC_MAGE"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
export SNOWFLAKE_DATABASE="DB_TLC"
export SNOWFLAKE_SCHEMA_SILVER="SILVER"
export SNOWFLAKE_SCHEMA_GOLD="GOLD"

```

### 5.3 Estructura del proyecto

```
/home/src/dbt/
  profiles.yml
  /nyc_tlc/
    dbt_project.yml
    models/
      sources/
        sources.yml
      silver/
        trips_cleaned.sql
        schema.yml
      gold/
        dim_zone.sql
        fct_trips.sql
        schema.yml
    macros/
    seeds/ (opcional)

```

### 5.4 profiles.yml

```yaml
# /home/src/dbt/profiles.yml
nyc_tlc:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA_SILVER') | default('SILVER') }}"
      threads: 4

```

### 5.5 dbt_project.yml

```yaml
# /home/src/dbt/nyc_tlc/dbt_project.yml
name: nyc_tlc
version: "1.0"
profile: nyc_tlc

models:
  nyc_tlc:
    +on_schema_change: append_new_columns
    silver:
      +schema: "SILVER"
    gold:
      +schema: "GOLD"

```

> Comandos base
> 

```bash
source /home/src/.venvs/dbt/bin/activate
source /home/src/dbt/env.dbt

dbt debug --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt
dbt run   --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --select silver
dbt run   --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --select gold
dbt test  --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --select silver gold
```

> 
> 
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%206.png)
> 

---

## 6) Calidad (tests dbt) + documentación (descriptions)

### 6.1 Tests en SILVER

```yaml
# models/silver/schema.yml
version: 2

models:
  - name: trips_cleaned
    description: "Viajes NYC estandarizados (SILVER)."
    columns:
      - name: pickup_datetime
        tests: [not_null]
      - name: dropoff_datetime
        tests: [not_null]
      - name: pickup_date
        tests: [not_null]
      - name: pickup_location_id
        tests: [not_null]
      - name: dropoff_location_id
        tests: [not_null]
      - name: service_type
        description: "yellow | green"
        tests:
          - accepted_values:
              values: ["yellow", "green"]

```

### 6.2 Tests en GOLD

```yaml
# models/gold/schema.yml
version: 2

models:
  - name: dim_zone
    description: "Dimensión de zonas TLC."
    columns:
      - name: zone_id
        tests: [not_null, unique]

  - name: fct_trips
    description: "Hechos de viajes (grain: 1 fila por viaje)."
    columns:
      - name: pickup_date
        tests: [not_null]
      - name: pickup_location_id
        tests: [not_null]
      - name: service_type
        tests:
          - accepted_values:
              values: ["yellow", "green"]

```

> 
> 
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%207.png)
> 

---

## 7) Auditoría y calidad adicional

**Conteos por mes/servicio (RAW vs SILVER vs GOLD)**

> 
> 

```sql
-- RAW (auditoría por manifest)
SELECT YEAR, MONTH, SERVICE_TYPE,
       SUM(ROWS_LOADED) AS rows_loaded
FROM DB_TLC.RAW.LOAD_AUDIT
WHERE STATUS='OK'
GROUP BY 1,2,3
ORDER BY 1,2,3;
```

```sql
-- SILVER
SELECT pickup_year, pickup_month, service_type, COUNT(*) AS rows
FROM DB_TLC.SILVER.TRIPS_CLEANED
GROUP BY 1,2,3
ORDER BY 1,2,3;

```

```sql
-- GOLD (hechos)
SELECT YEAR(pickup_datetime) AS y, MONTH(pickup_datetime) AS m,
       service_type, COUNT(*) AS rows
FROM DB_TLC.GOLD.FCT_TRIPS
GROUP BY 1,2,3
ORDER BY 1,2,3;
```

---

## 8) Clustering en `GOLD.FCT_TRIPS`

> Estrategia
> 
> 
> Claves elegidas: `pickup_date`, `pickup_location_id`, `service_type`.
> 
> Justificación: consultas por fecha/mes + zona + servicio se benefician del pruning.
> 

**A) Crear/forzar clustering (si tu edición lo soporta):**

```sql
-- Si tu edición de Snowflake soporta clustering automático:
CREATE OR REPLACE TABLE DB_TLC.GOLD.FCT_TRIPS CLUSTER BY (pickup_date, pickup_location_id, service_type) AS
SELECT * FROM DB_TLC.GOLD.FCT_TRIPS;

-- O, si la tabla ya existe (y tu edición soporta):
ALTER TABLE DB_TLC.GOLD.FCT_TRIPS CLUSTER BY (pickup_date, pickup_location_id, service_type);
```

**B) Medir clustering:**

```sql
SELECT SYSTEM$CLUSTERING_INFORMATION('DB_TLC.GOLD.FCT_TRIPS',
                                     '(pickup_date, pickup_location_id, service_type)') AS info;

```

> 
> 
> - `info` de clustering (si disponible).
> 
> ![image.png](Deber%202%20%E2%80%9CProyecto%2002%20%E2%80%94%20NYC%20TLC%20Analytics%20Engineeri%20284fbe7dbe3180f09454e20598338b4f/image%208.png)
> 

---

## 9) Documentación dbt (docs + lineage)

```bash
# Genera y sirve docs
dbt docs generate --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt
dbt docs serve    --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --port 8085

```

---

## 10) Entregables (GitHub)

- **Repositorio** con:
    - `docker-compose.yml` (contiene Mage)
    - Proyecto **Mage** (pipelines de ingesta y de transformaciones dbt)
    - Proyecto **dbt** (silver/gold, tests, docs)
    - `README.md` con:
        - Arquitectura y orquestación
        - Matriz de cobertura 2015–2025
        - Pipeline de backfill mensual + idempotencia
        - Gestión de secrets + rol/usuario mínimo privilegio
        - Diseño silver/gold + clustering (keys, métricas, conclusiones)
        - Pruebas y cómo interpretarlas
        - Troubleshooting (abajo)
- **Evidencias** (carpeta `/evidence/`): capturas pedidas.
- **Notebook** `data_analysis.ipynb` para las 5 preguntas (ver §11).

---

## 12) Troubleshooting (resumen rápido)

- **`Insufficient privileges` al correr dbt:**
    
    Revisa `GRANT USAGE` en `DB_TLC` y `SCHEMAS`, y `CREATE TABLE` en `SILVER/GOLD`.
    
    Comprueba el rol activo:
    
    ```sql
    SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA();
    ```
    
- **Mage conectaba solo con `PUBLIC`:**
    
    No pases `role` en el connect si no está concedido; luego ejecuta `USE ROLE R_DP_TLC_MAGE` dentro de la sesión (o ajusta secrets y grants hasta que sea válido).
    
- **Clustering “Unsupported feature 'RECLUSTER'”:**
    
    Documenta limitación de edición. Mantén CLUSTER BY lógico en diseño y usa Query Profile para evidenciar pruning con filtros por fecha/zona.
    
- **dbt `invalid identifier` (nombres con comillas):**
    
    Normaliza columnas en SILVER (`lower_snake_case`) y usa alias consistentes.
    

---

## 14) Comandos generales

```bash
# Activar entorno
source /home/src/.venvs/dbt/bin/activate
source /home/src/dbt/env.dbt

# dbt lifecycle
dbt debug --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt
dbt run   --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --select silver
dbt run   --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --select gold
dbt test  --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --select silver gold

# Docs
dbt docs generate --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt
dbt docs serve    --project-dir /home/src/dbt/nyc_tlc --profiles-dir /home/src/dbt --port 8085

```