# Deber 1 Erick Daniel Suárez Veloz

# QuickBooks Backfill Pipelines con Mage + Postgres

## 1. Descripción general

Este deber implementa la ingesta histórica (**backfill**) de tres entidades de **QuickBooks Online (QBO)**:

- **Invoices**
- **Customers**
- **Items**

La orquestación se realiza con **Mage AI** y la persistencia en la capa **RAW de Postgres**.

El diseño garantiza: **idempotencia, segmentación, manejo de rate limits, paginación, seguridad en secretos y validación de datos**.

📌 **Diagrama de arquitectura realizado en [draw.io](http://draw.io) (**https://drive.google.com/file/d/1sbg9ByPptIfH-ruTswj9eD5OyoXMGu0V/view?usp=sharing)

![image.png](attachment:22434b6e-d577-4016-ba90-530a674e79e8:image.png)

---

## 2. Infraestructura Docker

- **Servicios** definidos en `docker-compose.yml`:
    - `postgres` (con persistencia en `./warehouse_data`)
    - `pgadmin` (interfaz de administración)
    - `mage` (orquestador)
- Todos los servicios se encuentran en la red **qb-net**.
- Persistencia habilitada en volúmenes para no perder datos al reiniciar.

**Captura de un “Docker ps” para ver que los contenedores están arriba:**

![image.png](attachment:244c9913-a1c3-455a-9142-d208884be0e2:image.png)

---

## 3. Gestión de secretos

Todos los **secrets** se gestionan en Mage (`Secrets Manager`).

- **QuickBooks:**
    - `qb_realm_id`
    - `qb_client_id`
    - `qb_client_secret`
    - `qb_access_token`
    - `qb_refresh_token`
- **Postgres:**
    - `POSTGRES_USER`
    - `POSTGRES_PASSWORD`
    - `POSTGRES_HOST`
    - `POSTGRES_PORT`
    - `POSTGRES_DB`

**Nota importante:** los valores nunca están en el repo, solo sus nombres y propósito.

**Captura de la sección “Secrets” en mi Mage:**

![image.png](attachment:309f8409-2ed6-4aff-8c21-c4b05aebff64:image.png)

---

## 4. Pipelines implementados

Se construyeron **3 pipelines parametrizados**:

- `qb_invoices_backfill`

![image.png](attachment:720552b3-df36-4f0f-a799-bbf73e76e462:image.png)

- `qb_customers_backfill`

![image.png](attachment:23c1bbb1-1809-45f8-98e1-84c6b8f33fa1:image.png)

- `qb_items_backfill`

![image.png](attachment:acb7d9a0-175c-4c9b-9234-7e886c879944:image.png)

Cada pipeline incluye:

1. **Loader**
    - Consulta API QBO con OAuth 2.0.
    - Segmentación semanal (`fecha_inicio` → `fecha_fin`).
    - Paginación (1000 registros máx).
    - Refresh automático de tokens.
2. **Transformer**
    - Normaliza la respuesta en un DataFrame tabular.
    - Extrae campos clave (`Id`, fechas, montos, referencias).
    - Guarda el `payload` completo como JSON.
3. **Exporter**
    - Inserta los datos en Postgres RAW (`raw.qb_<entidad>`).
    - Convierte `payload` a JSONB.
    - Asegura idempotencia (claves primarias + payload completo).

**Captura de los 3 pipelines:**

![image.png](attachment:565e73f6-a046-460a-9fe5-b9b0cef25385:image.png)

---

## 5. Esquema RAW en Postgres

Cada entidad tiene su tabla en el esquema `raw`:

- `raw.qb_invoices`
- `raw.qb_customers`
- `raw.qb_items`

![image.png](attachment:47c00799-8fcf-497c-aaf7-17d53f325082:image.png)

Columnas comunes:

- `entity`
- `fecha_inicio_utc`, `fecha_fin_utc`
- `page_number`, `page_size`
- `request_payload`
- Campos principales de negocio (Id, Name, DocNumber, TotalAmt, etc.)
- `payload` (JSONB con el registro completo de QBO).

**Captura Pg Admin de los 100 primeros registros de la tabla qb_invoices:**

![image.png](attachment:b94ad4a9-41a6-4d7a-b94e-b54f870aab64:image.png)

---

## 6. Trigger One-Time

Se configuró un **trigger one-time en Mage** para lanzar los pipelines de backfill.

- Fecha/hora definida en **UTC** y documentada con equivalencia a **Guayaquil (GMT-5)**.
- Configuración incluye **entity + fecha_inicio + fecha_fin**.
- Tras ejecución, el trigger se **deshabilita** para evitar reejecuciones accidentales.

**Captura Triggers de invoices, customers e ítems:**

![Captura de pantalla 2025-09-12 a la(s) 15.45.08.png](attachment:3065461b-6f5b-4815-bb6b-4794576f56fd:Captura_de_pantalla_2025-09-12_a_la(s)_15.45.08.png)

![Captura de pantalla 2025-09-12 a la(s) 15.44.51.png](attachment:7fa83a76-380a-4a45-8254-7e558643ccab:Captura_de_pantalla_2025-09-12_a_la(s)_15.44.51.png)

![Captura de pantalla 2025-09-12 a la(s) 15.45.01.png](attachment:7774a801-dfc8-4b00-a513-884ac45cd883:Captura_de_pantalla_2025-09-12_a_la(s)_15.45.01.png)

---

## 7. Validaciones y volumetría

- **Volumetría:** se registró cantidad de filas por tramo y por entidad.
- **Validaciones mínimas:**
    - Cada fila contiene `Id` y `payload`.
    - No existen duplicados de `Id` dentro de una misma entidad.
    - Las fechas (`TxnDate`, `MetaData.LastUpdatedTime`) están dentro del rango solicitado.

**Captura de** consultas en pgAdmin con conteos (`SELECT COUNT(*) FROM raw.qb_invoices;`).

![image.png](attachment:4634e153-d6fb-4960-a020-4f7bb113bcb0:image.png)

---

## 8. Troubleshooting

Casos documentados:

- **Token expirado:** refresh automático en loader.

![image.png](attachment:8b08333b-4fd8-4aff-be57-802f05627ceb:image.png)

- **Pagos o clientes vacíos:** loader devuelve lista vacía y loggea advertencia.
- **Rate limits:** segmentación semanal + reintentos en loader.
- **Errores de exportación:** payload convertido a JSON string antes de exportar.
- **Timezone:** siempre se usa UTC (`Z`).
