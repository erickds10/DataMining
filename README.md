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

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image.png)

---

## 2. Infraestructura Docker

- **Servicios** definidos en `docker-compose.yml`:
    - `postgres` (con persistencia en `./warehouse_data`)
    - `pgadmin` (interfaz de administración)
    - `mage` (orquestador)
- Todos los servicios se encuentran en la red **qb-net**.
- Persistencia habilitada en volúmenes para no perder datos al reiniciar.

**Captura de un “Docker ps” para ver que los contenedores están arriba:**

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%201.png)

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

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%202.png)

---

## 4. Pipelines implementados

Se construyeron **3 pipelines parametrizados**:

- `qb_invoices_backfill`

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%203.png)

- `qb_customers_backfill`

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%204.png)

- `qb_items_backfill`

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%205.png)

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

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%206.png)

---

## 5. Esquema RAW en Postgres

Cada entidad tiene su tabla en el esquema `raw`:

- `raw.qb_invoices`
- `raw.qb_customers`
- `raw.qb_items`

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%207.png)

Columnas comunes:

- `entity`
- `fecha_inicio_utc`, `fecha_fin_utc`
- `page_number`, `page_size`
- `request_payload`
- Campos principales de negocio (Id, Name, DocNumber, TotalAmt, etc.)
- `payload` (JSONB con el registro completo de QBO).

**Captura Pg Admin de los 100 primeros registros de la tabla qb_invoices:**

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%208.png)

---

## 6. Trigger One-Time

Se configuró un **trigger one-time en Mage** para lanzar los pipelines de backfill.

- Fecha/hora definida en **UTC** y documentada con equivalencia a **Guayaquil (GMT-5)**.
- Configuración incluye **entity + fecha_inicio + fecha_fin**.
- Tras ejecución, el trigger se **deshabilita** para evitar reejecuciones accidentales.

**Captura Triggers de invoices, customers e ítems:**

![Captura de pantalla 2025-09-12 a la(s) 15.45.08.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/Captura_de_pantalla_2025-09-12_a_la(s)_15.45.08.png)

![Captura de pantalla 2025-09-12 a la(s) 15.44.51.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/Captura_de_pantalla_2025-09-12_a_la(s)_15.44.51.png)

![Captura de pantalla 2025-09-12 a la(s) 15.45.01.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/Captura_de_pantalla_2025-09-12_a_la(s)_15.45.01.png)

---

## 7. Validaciones y volumetría

- **Volumetría:** se registró cantidad de filas por tramo y por entidad.
- **Validaciones mínimas:**
    - Cada fila contiene `Id` y `payload`.
    - No existen duplicados de `Id` dentro de una misma entidad.
    - Las fechas (`TxnDate`, `MetaData.LastUpdatedTime`) están dentro del rango solicitado.

**Captura de** consultas en pgAdmin con conteos (`SELECT COUNT(*) FROM raw.qb_invoices;`).

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%209.png)

---

## 8. Troubleshooting

Casos documentados:

- **Token expirado:** refresh automático en loader.

![image.png](Deber%201%20Erick%20Daniel%20Su%C3%A1rez%20Veloz%2026cfbe7dbe3180efa237cc8d1ea7b642/image%2010.png)

- **Pagos o clientes vacíos:** loader devuelve lista vacía y loggea advertencia.
- **Rate limits:** segmentación semanal + reintentos en loader.
- **Errores de exportación:** payload convertido a JSON string antes de exportar.
- **Timezone:** siempre se usa UTC (`Z`).

---
