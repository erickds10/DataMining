# DEBER 4

# NYC TLC – PSet 4: Pipeline Spark + Postgres + Modelado de `total_amount`

Este repositorio contiene la solución del PSet 4 de Data Mining, que integra:

- **Ingesta de datos RAW (NYC TLC)** desde los Parquet públicos vía HTTP.
- **Carga en PostgreSQL** en un esquema `raw` con metadatos de ingesta.
- **Construcción de una tabla OBT** (`analytics.obt_trips`) mediante un script CLI `build_obt.py`.
- **Modelado de `total_amount`** usando:
    - Modelos **from-scratch en NumPy** (SGD, Ridge, Lasso, ElasticNet).
    - Modelos **equivalentes en scikit-learn**.
    - Comparación de métricas y tiempos.
- **Reproducibilidad** mediante Docker Compose y configuración vía `.env`.

---

## 1. Estructura del repositorio

```
dm-pset4/
├─ docker-compose.yml
├─ .env.example            # plantilla de variables de entorno
├─ sql/
│  └─ 00_init_schemas.sql  # crea esquemas raw / analytics
├─ obt-builder/
│  ├─ Dockerfile
│  ├─ build_obt.py         # script CLI para construir OBT
│  └─ requirements.txt
├─ notebooks/
│  ├─ 01_ingesta_parquet_raw.ipynb
│  └─ ml_total_amount_regression.ipynb
├─ logs/
│  ├─ obt_builder_*.log    # logs de ejecución de build_obt
│  └─ ml_results_*.md      # tabla comparativa de modelos
└─ README.md
```

![image.png](DEBER%204/image.png)

## **2.  Docker Compose y servicios**

El archivo docker-compose.yml levanta 3 servicios:

1. **postgres**
    - Imagen: postgres:16
    - Esquemas: raw, analytics (creados desde ./sql/00_init_schemas.sql)
    - Datos persistentes en volumen pgdata
2. **spark-notebook**
    - Imagen: jupyter/pyspark-notebook:latest
    - Expone Jupyter en http://localhost:8888/?token=taxi
    - Monta ./notebooks en /home/jovyan/work
    - Aquí se ejecutan los notebooks de ingesta y ML.
3. **obt-builder**
    - Imagen build desde ./obt-builder
    - Contiene build_obt.py y dependencias de SQLAlchemy / psycopg2.
    - Se usa para crear la tabla analytics.obt_trips leyendo desde raw.

### **2.1 Variables de entorno (.env)**

Crear un archivo .env en la raíz del proyecto basado en .env.example:

`PG_HOST=postgres
PG_PORT=5432
PG_DB=nyc_taxi
PG_USER=postgres
PG_PASSWORD=password`

`PG_SCHEMA_RAW=raw
PG_SCHEMA_ANALYTICS=analytics`

`SPARK_DRIVER_MEMORY=4g`

`RUN_ID=pset4_dev`

## **3. Cómo levantar el entorno con Docker Compose**

Desde la raíz del proyecto:

```jsx
docker compose up -d
```

- Esto levanta:
    - pset4-postgres (PostgreSQL)
    - pset4-spark (Jupyter con PySpark)
- Verificar contenedores:

```jsx
docker ps
```

Para entrar al notebook:

1. Abrir navegador en: http://localhost:8888/?token=taxi
2. Navegar a la carpeta work/
3. Abrir:
    - 01_ingesta_parquet_raw.ipynb
    - ml_total_amount_regression.ipynb
    - Models.ipynb

## **4. Ingesta RAW desde Parquet (01_ingesta_parquet_raw.ipynb)**

Este notebook:

1. **Descarga** los archivos Parquet desde:
    - https://d37ci6vzurychx.cloudfront.net/trip-data/*
2. Hace **streaming por lotes** (PyArrow) para no matar la RAM:
    - Convierte cada RecordBatch a pandas
    - Normaliza nombres de columnas a un esquema común
    - Aplica coerciones robustas de tipo (evita StructType, pd.NA, etc.)
    - Genera un DataFrame de Spark con un esquema explícito (SPARK_SCHEMA)
3. Escribe en PostgreSQL vía .write.jdbc, agregando metadatos:
    - source_year, source_month, service_type
    - run_id, ingested_at_utc

### **4.1 Esquema RAW**

Las tablas creadas (DDL) son:

- raw.yellow_taxi_trip
- raw.green_taxi_trip
- raw.taxi_zone_lookup

Cada tabla incluye:

- Campos originales del viaje (pickup_datetime, trip_distance, fare_amount, etc.)
- Metadatos:
    - source_year, source_month, service_type
    - run_id, ingested_at_utc

### **4.2 Rango temporal**

El pipeline está parametrizado para soportar **2015–2025**, por ejemplo:

```jsx
services = ["yellow", "green"]
years = range(2023, 2024)
months = range(1, 13)
```

OJO: Por qué solo cargué 2 años?? porque tenía unicamente 20gb de disco en mi compu, y entre cargar la bd de postgres y el OBT, ya no tuve espacio. 

En este PSet, por restricciones de espacio/tiempo, ejecuté la ingesta solo para:

- years = [2023, 2024]

pero el código permite extender fácilmente a 2015–2025 cambiando esos parámetros.

### **4.3 Cómo ejecutar la ingesta RAW**

En el notebook 01_ingesta_parquet_raw.ipynb:

1. Ejecutar las celdas de configuración (Spark, Postgres, URLs).
2. Ejecutar la celda que crea los DDL de las tablas RAW.
3. Ejecutar el bucle de ingesta, por ejemplo:

`services = ["yellow", "green"]
years = [2023, 2024]
months = range(1, 13)`

`for svc in services:
for y in years:
for m in months:
ingest_month_batched(svc, y, m, batch_rows=100_000)`

4. Al final, correr la celda de conteo:

```jsx
for t in ["yellow_taxi_trip","green_taxi_trip","taxi_zone_lookup"]:
print("raw." + t, "→", quick_count(t))
```

![image.png](DEBER%204/image%201.png)

![image.png](DEBER%204/image%202.png)

## **5. Construcción de la OBT con**

## **build_obt.py**

El script obt-builder/build_obt.py es un **CLI reproducible** que:

- Lee desde raw.yellow_taxi_trip y raw.green_taxi_trip
- Hace UNION ALL
- Enlaza con raw.taxi_zone_lookup para obtener borough/zone
- Calcula features derivados:
    - pickup_date, pickup_hour, pickup_dow
    - trip_duration_min
    - avg_speed_mph
    - tip_pct
- Escribe la tabla final analytics.obt_trips

![image.png](DEBER%204/image%203.png)

### **5.1 Modo**

### **full**

Reconstruye la OBT completa para el rango de años especificado.

```jsx
docker compose run --rm obt-builder \
--mode full \
--year-start 2015 \
--year-end 2025 \
--services yellow,green \
--run-id pset4_full \
--overwrite true
```

En este PSet, para 2023–2024:

```jsx
docker compose run --rm obt-builder \
--mode full \
--year-start 2023 \
--year-end 2024 \
--services yellow,green \
--run-id pset4_2023_2024 \
--overwrite true
```

Comportamiento:

- Si --overwrite true:
    - Hace DROP TABLE analytics.obt_trips si existe.
    - Crea de nuevo la tabla.
    - Inserta partición por partición (year, month).
- En consola se imprime:
    - Parámetros
    - Mensaje por partición:
        
        ➡️ Insertando partición 2023-01 … ✅ Partición 2023-01 insertada
        

### **5.2 Modo**

### **by-partition**

### **(idempotente)**

Permite reconstruir **solo una partición** (year, month) sin duplicar filas.

Ejemplo:

```jsx
docker compose run --rm obt-builder \
--mode by-partition \
--year-start 2023 \
--year-end 2023 \
--services yellow,green \
--run-id pset4_patch_2023_01 \
--overwrite true \
--month 1
```

Comportamiento:

- Antes de insertar, ejecuta algo como:

```jsx
DELETE FROM analytics.obt_trips
WHERE source_year = :year AND source_month = :month;
```

- Luego inserta solo esa partición → **idempotencia garantizada**.

### **5.3 Evidencias**

![image.png](DEBER%204/image%204.png)

## **6. Notebook de modelado:**

## **ml_total_amount_regression.ipynb y Models.ipynb**

Estos notebooks implementan:

1. **Carga de datos desde analytics.obt_trips** (vía SQLAlchemy).
2. Filtros de calidad:
    - total_amount entre 1 y 250
    - trip_distance_miles entre 0.1 y 100
    - trip_duration_min entre 1 y 240
    - avg_speed_mph entre 0.1 y 120
    - passenger_count entre 1 y 6
3. **Subsample controlado** (ej. 300k filas) para no saturar la RAM.
4. Split Train/Val/Test (sin leakage, con split temporal y seed fija).
5. Preprocesamiento común:
    - Imputación (num: mediana, cat: moda)
    - Escalado numérico (StandardScaler)
    - PolynomialFeatures grado 2
    - OneHotEncoder para categóricas
6. **Baselines**:
    - Media de train
    - Regresión lineal simple
7. **Modelos from-scratch (NumPy)**:
    - SGD (MSE)
    - Ridge (L2)
    - Lasso (L1)
    - ElasticNet (L1+L2)
    - GridSearch manual con:
        - registro de hiperparámetros
        - tiempos de entrenamiento
        - métricas en validación (RMSE/MAE/R²)
8. **Modelos scikit-learn equivalentes**:
    - SGDRegressor
    - Ridge
    - Lasso
    - ElasticNet
    - GridSearchCV / validación cruzada
9. **Tabla comparativa final**:
    - 8 filas (4 from-scratch, 4 sklearn)
    - Columnas:
        - model
        - rmse_val, mae_val, r2_val
        - rmse_test, mae_test, r2_test
        - train_time_s
        - n_coefs
10. **Selección final**:
    - Modelo ganador: Lasso_sklearn
        - Menor RMSE_val
        - Buen R²
        - Menor número de coeficientes no cero
11. **Reentrenamiento en Train+Val y evaluación en Test**.
12. **Diagnóstico de errores**:
    - Gráfico y_true vs y_pred
    - Histograma de residuales
    - Boxplot de errores por bucket de total_amount o por borough/hora.

## CONCLUSIONES ENTRENAMIENTO MODELOS (**Diagnóstico final)**

- El modelo **no presenta sesgos sistemáticos**.
- Los residuos están centrados en 0.
- La relación *pred vs real* es lineal y estable.
- Los errores aumentan ligeramente con montos altos (por escasez de datos).
- No se observan patrones que justifiquen un modelo más complejo (árboles boosting o redes).

**Conclusión del diagnóstico:**

*El modelo es robusto, estable y suficientemente preciso para producción dentro del alcance del PSET.*

# **Conclusiones: Operatividad, reentrenamiento y producción**

# **12.1 Conclusiones (texto para informe)**

El modelo ganador fue **Lasso (scikit-learn)**, con un desempeño de:

- **RMSE_test = 2.094**
- **MAE_test ≈ 1.15**
- **R²_test ≈ 0.9911**

Estos valores representan un **salto enorme** respecto al baseline (RMSE ≈ 22), lo que evidencia que el modelo captura de manera efectiva las relaciones lineales entre distancia, duración, propinas, ubicación y horario.

Lasso fue seleccionado no solo por ser el mejor en validación, sino por su **simplicidad**, **estabilidad** y el hecho de que reduce coeficientes, lo cual **mejora interpretabilidad y generalización**. Además, obtuvo el menor RMSE entre todos los modelos comparados en validación, cumpliendo exactamente con lo solicitado en el PSET.

# **Por qué Lasso es el modelo operativo**

### **Estabilidad y simplicidad**

- Menos coeficientes → menor riesgo de sobreajuste.
- Modelo lineal → rápido de entrenar y fácil de explicar.

### **Buen rendimiento fuera de muestra**

- Gap muy pequeño entre Val y Test → **sin overfitting**.
- Funciona bien incluso en buckets altos.

### **Regularización L1**

- Selecciona automáticamente variables relevantes.
- Reduce dimensionalidad efectiva sin necesidad de feature selection manual.

## EVIDENCIAS

![image.png](DEBER%204/image%205.png)

- Tabla final de métricas en las que se demuestran los resultados scratch vs sklearn.

![image.png](DEBER%204/image%206.png)

- Resultado de docker ps -a para ver los contenedores corriendo los servicios.

![image.png](DEBER%204/image%207.png)

- Imagen de espacio en disco antes de realizar el deber

![image.png](DEBER%204/image%208.png)

- Imagen del peso del volumen del deber en GB.

![image.png](DEBER%204/image%209.png)

- Imagen de los schemas creados para garantizar la carga de datos del par de años seleccionado. Se genera al ejecutar:

`docker exec -it pset4-postgres psql -U postgres -d nyc_taxi`

`\dn        -- listas los esquemas
\dt raw.*`

![image.png](DEBER%204/image%2010.png)

- Imagen del schema de analytics, que se genera al ejecutar:

`docker exec -it pset4-postgres bash
psql -U postgres -d nyc_taxi`

`\dn        -- lista esquemas
\dt analytics.*`

`SELECT COUNT(*) FROM analytics.obt_trips;`