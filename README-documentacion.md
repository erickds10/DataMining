# DataMining — PSET 3 (NYC Taxi + Snowflake)

## Contenido
- `notebooks/`: Jupyter con ingesta (RAW), modelado (ANALYTICS), y preguntas de negocio.
- `docker-compose.yml`: entorno de Jupyter/PySpark.
- `imagenes-documentación/`: capturas usadas en el informe.
- `jdbc_jars/README.md`: instrucciones para descargar los JARs (no versionados).
- `link-documentacion-notion.txt`: enlace a la documentación completa.

## Reproducir
1. `docker compose up -d`  
2. Abrir `http://localhost:8888` y ejecutar notebooks en orden:
   - 01_ingesta_raw.ipynb
   - 02_obt_analytics.ipynb
   - 03_preguntas_negocio.ipynb
3. Snowflake:
   - Role: `R_DM_P3`, Warehouse: `WH_DM_P3`, DB: `DB_TLC`
   - Schemas: `RAW`, `ANALYTICS`
4. Variables (no versionadas): `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USER`, `SNOWFLAKE_PASSWORD`, etc.

## Notas
- No se versionan binarios grandes ni credenciales.
- Ver documentación en Notion (link en el repo).
