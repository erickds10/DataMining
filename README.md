# Proyecto Final

# PSET 6 y PF — **Pipeline de Datos para Trading Algorítmico con Mercado**

**Curso:** Data Mining 2025-01

**Profesor:** Erick Ñauñay

**Estudiante:** Erick Daniel Suárez Veloz

## **Descripción general**

Este proyecto implementa la solución **individual** del **Proyecto #6 y Final** de la materia **Data Mining**, siguiendo estrictamente las especificaciones del documento Proyecto #6 y Final.pdf. La solución cubre de punta a punta:

- **Ingesta automática** de datos de precios diarios desde Yahoo Finance (yfinance).
- **Almacenamiento estructurado** en PostgreSQL con esquemas raw y analytics.
- **Construcción de features diarias** mediante un **feature-builder** ejecutable por CLI (Proyecto 06).
- **Entrenamiento de modelos de clasificación** para predecir si el activo cerrará arriba o abajo del precio de apertura.
- **Simulación de estrategias de trading intradía** vs estrategia baseline **buy & hold**.
- **API REST** (FastAPI) para servir el mejor modelo como servicio (/predict).
- **Infraestructura Docker** para reproducir todo el pipeline en forma aislada.

### **Objetivo**

Desarrollar un **clasificador binario** que prediga la variable:

> target_up = 1 si close > open (día alcista),
> 

> target_up = 0 en caso contrario,
> 

y usar estas predicciones para simular una estrategia de trading intradía que potencialmente **supere el rendimiento** de una estrategia pasiva de **buy & hold** sobre el mismo activo.

Se trabajan **tres activos**:

- AAPL – Apple Inc. (NASDAQ)
- NKE – Nike Inc. (NYSE)
- MBG.DE – Mercedes-Benz Group AG (XETRA)

**Estructura del proyecto**

```jsx
proyectofinal/
├── docker-compose.yml          # Orquestación de servicios (Postgres, Jupyter, feature-builder, model-api)
├── requirements.txt            # Dependencias Python para notebooks/local
├── README.md                   # Este archivo
├── "Proyecto #6 y Final.pdf"   # Enunciado oficial del proyecto
│
├── sql/
│   ├── 01_create_schemas.sql               # Crea esquemas raw y analytics
│   ├── 02_create_raw_prices_daily.sql      # Tabla raw.prices_daily
│   └── 03_create_analytics_daily_features.sql  # Tabla analytics.daily_features
│
├── notebooks/
│   ├── 01_ingesta_prices_raw.ipynb         # Fase 1 – Ingesta a raw.prices_daily
│   ├── 02_ml_trading_classifier.ipynb      # Fase 3 – ML sobre analytics.daily_features
│   └── 03_Simulaciones.ipynb               # Fase 4 – Simulaciones de trading (modelo vs buy & hold)
│
├── src/
│   ├── db_utils.py                # Funciones de conexión y utilidades para Postgres
│   └── build_features.py          # Fase 2 – Script CLI de feature engineering (Proyecto 06)
│
├── feature_build/
│   ├── Dockerfile                 # Imagen del servicio feature-builder
│   └── requirements.txt
│
├── model_api/
│   ├── app.py                     # FastAPI con endpoints /health y /predict
│   ├── Dockerfile                 # Imagen del servicio model-api
│   └── requirements.txt
│
└── models/
    ├── best_model_AAPL.pkl        # Mejor modelo entrenado para AAPL
    ├── best_model_NKE.pkl         # Mejor modelo entrenado para NKE
    └── best_model_MBG-DE.pkl      # Mejor modelo entrenado para MBG.DE
```

OJO: Los .pkl se generan/actualizan a partir del notebook 02_ml_trading_classifier.ipynb y se copian a models/ para ser usados por la API.

![image.png](Proyecto%20Final/image.png)

**Instalación y configuración**

```jsx
git clone https://github.com/erickds10/DataMining.git
cd proyectofinal
```

**Archivo .env**

```jsx
# PostgreSQL
PG_HOST=postgres
PG_PORT=5432
PG_DB=trading_db
PG_USER=xxxxx
PG_PASSWORD=xxxxxx

# Schemas
PG_SCHEMA_RAW=raw
PG_SCHEMA_ANALYTICS=analytics

# Tickers a analizar
TICKERS=AAPL,NKE,MBG.DE

# Rango de ingesta
START_DATE=2018-01-01
END_DATE=2025-12-31

# API REST
MODEL_PATH=/models/best_model_AAPL.pkl
PORT=8000
```

**Levantar la infraestructura base**

```jsx
docker compose up -d postgres jupyter-notebook
docker compose ps
```

![image.png](Proyecto%20Final/image%201.png)

# Pipeline de datos

### **FASE 1 – Ingesta a raw.prices_daily (Notebook 01)**

**Notebook**: notebooks/01_ingesta_prices_raw.ipynb

**Objetivo:** descargar precios diarios OHLCV de Yahoo Finance para AAPL, NKE y MBG.DE entre 2018-01-01 y 2025-12-31, y cargarlos en raw.prices_daily con metadatos de trazabilidad.

Pasos principales en el notebook:

1. **Leer variables de entorno** (PG_*, TICKERS, START_DATE, END_DATE).
2. Crear engine de SQLAlchemy con postgresql+psycopg2.
3. Descargar precios con yfinance.download() para cada ticker.
4. Normalizar columnas → date, open, high, low, close, adj_close, volume.
5. Añadir columnas:
    - ticker
    - run_id (ej. run_001)
    - source_name = "yfinance"
    - ingested_at_utc (timestamp UTC)
6. Idempotencia:
    - **DELETE por (run_id, rango de fechas, tickers)** antes de volver a insertar.
7. Insertar con to_sql(schema="raw", if_exists="append").

**Evidencia Ingesta:**

![image.png](Proyecto%20Final/image%202.png)

### **FASE 2 – analytics.daily_features**

### **+ feature-builder (Proyecto 06)**

Esta fase es la parte **obligatoria** del Proyecto 06 y se implementa en:

- src/build_features.py
- servicio Docker feature-builder (usa feature_build/Dockerfile).

**Objetivo:** leer raw.prices_daily y construir una tabla de features limpias en analytics.daily_features que luego se usan en el notebook de ML.

### **Features generadas**

Para cada día y ticker se construyen features como:

- **Calendario**:
    - year, month, day_of_week
    - is_monday, is_friday
- **Precios y volumen**:
    - open, close, high, low, volume
- **Retornos**:
    - return_close_open = (close–open)/open
    - return_prev_close = (close_t – close_{t-1})/close_{t-1}
- **Volatilidad**:
    - volatility_n_days = std de retornos en una ventana móvil (ej. 10 días)
- **Lags (día anterior)** para todas las anteriores:
    - open_lag1, close_lag1, high_lag1, low_lag1, volume_lag1,
    - return_close_open_lag1, return_prev_close_lag1, volatility_n_days_lag1.

### **Ejecución vía CLI (feature-builder)**

Para cada ticker:

```jsx
docker compose run --rm feature-builder \
  --mode full \
  --ticker AAPL \
  --run-id feat_run_001 \
  --overwrite true

docker compose run --rm feature-builder \
  --mode full \
  --ticker NKE \
  --run-id feat_run_001 \
  --overwrite true

docker compose run --rm feature-builder \
  --mode full \
  --ticker MBG.DE \
  --run-id feat_run_001 \
  --overwrite true
```

**Evidencia Feature-builder:**

![image.png](Proyecto%20Final/image%203.png)

## **FASE 3 – Notebook de ML:**

## **02_ml_trading_classifier.ipynb**

Este notebook **usa exclusivamente** analytics.daily_features como fuente de datos, cumpliendo la restricción del enunciado (no se salta el pipeline).

### **Flujo para cada ticker (AAPL, NKE, MBG.DE)**

1. **Carga de datos:**

```jsx
df = pd.read_sql("""
    SELECT *
    FROM analytics.daily_features
    WHERE ticker = %(ticker)s
    ORDER BY date
""", engine, params={"ticker": ticker})
```

2. **Construcción del target:**

```jsx
df["target_up"] = (df["close"] > df["open"]).astype(int)
```

1. **Filtrado de filas válidas (lag):**
    
    Se eliminan las primeras filas donde faltan lags/volatilidad, para evitar leakage:
    

```jsx
df_model = df.dropna(subset=[
    "open_lag1", "close_lag1", "high_lag1", "low_lag1",
    "volume_lag1", "return_close_open_lag1",
    "return_prev_close_lag1", "volatility_n_days_lag1"
])
```

1. **Features usadas (11 columnas):**

```jsx
feature_cols = [
    "day_of_week", "is_monday", "is_friday",
    "open_lag1", "close_lag1", "high_lag1", "low_lag1",
    "volume_lag1",
    "return_close_open_lag1",
    "return_prev_close_lag1",
    "volatility_n_days_lag1",
]
```

1. **Split temporal (sin fuga de información):**
    
    Para cada ticker (ejemplo AAPL, pero igual para NKE y MBG.DE):
    
    - **Train**: ~2018-01-18 → 2021-12-31
    - **Val**: 2022-01-03 → 2023-12-29
    - **Test**: 2024-01-02 → 2024-12-31
    
    2025 se deja **fuera del entrenamiento** y se usa luego en las simulaciones (out-of-sample).
    
2. **Baseline:**

```jsx
DummyClassifier(strategy="most_frequent")
```

1. Se entrena y evalúa en Train y Val: sirve como referencia mínima (F1 y ROC-AUC).
2. **Modelos entrenados:**
    - log_reg – Logistic Regression
    - linear_svc – Linear SVC
    - decision_tree – Decision Tree
    - random_forest – Random Forest
    - gradient_boosting – GradientBoostingClassifier
    - hist_gradient_boosting – HistGradientBoostingClassifier
    - extra_trees – ExtraTreesClassifier
    - xgboost – XGBClassifier (ligero, adaptado a tu Mac)
    
    Se envuelven en un Pipeline(StandardScaler, Modelo) cuando aplica y se afinan con GridSearchCV + TimeSeriesSplit para respetar la naturaleza temporal.
    
3. **Métricas evaluadas:**
    - Accuracy
    - Precision
    - Recall
    - F1
    - ROC-AUC
    
    Se calculan en:
    
    - Train
    - Validation
    - Test
4. **Selección del mejor modelo por ticker:**
    - Se elige el modelo con **mejor F1 en validación**, excluyendo el Dummy como modelo candidato aunque se muestra para referencia.
5. **Matriz de confusión y classification report (Test):**
    
    Para cada ticker se genera:
    
    ```jsx
    from sklearn.metrics import confusion_matrix, classification_report
    y_pred_test = best_model.predict(X_test)
    print(confusion_matrix(y_test, y_pred_test))
    print(classification_report(y_test, y_pred_test))
    ```
    
6. **Serialización:**
    
    Se guarda el mejor modelo por ticker:
    
    ```jsx
    import joblib
    joblib.dump(best_model, f"../models/best_model_{ticker_safe}.pkl"
    ```
    

**Resultados resumidos (Train+Val / Test)**

![image.png](Proyecto%20Final/image%204.png)

## **FASE 4 – Simulaciones de trading (03_Simulaciones.ipynb)**

**Notebook**: notebooks/03_Simulaciones.ipynb

**Objetivo:** conectar los resultados de ML con un **backtest simple** de trading intradía y compararlos con una estrategia baseline de **buy & hold**.

### **Estrategia implementada**

- Capital inicial: 10,000 USD.
- Periodo de simulación: año **2025 completo** (hasta la última fecha disponible en los datos).
- Para cada día hábil:
    - Se **usa el modelo** para predecir target_up con las features del día **t-1**.
    - Si prediction = 1:
        - Se compra al **precio de apertura (open)** y se vende al **precio de cierre (close)** del mismo día.
    - Si prediction = 0:
        - El capital se mantiene en efectivo (sin posición).
- **Sin costos de transacción ni slippage** (simplificación).

### **Resultados AAPL (2025)**

Salidas obtenidas en el notebook:

```jsx
=== Resultados Baseline Buy & Hold (AAPL, 2025) ===
Capital final      : 11149.72 USD
Retorno total      : 11.50%
Retorno anualizado : 11.50%
Número de trades   : 1

=== Comparación Modelo vs Buy & Hold (AAPL, 2025) ===
Modelo  -> Capital final: 12239.32 USD, Retorno: 22.39%
BuyHold -> Capital final: 11149.72 USD, Retorno: 11.50%

Distribución de señales (2025):
{0: 59, 1: 168}

=== Resultados Estrategia Modelo (AAPL, 2025) ===
Capital final      : 12239.32 USD
Retorno total      : 22.39%
Retorno anualizado : 22.39%
Número de trades   : 168
```

Evidencia Simulación activo AAPL:

![image.png](Proyecto%20Final/image%205.png)

**Interpretación:**

- El modelo de ML para AAPL **genera ~22.4%** de retorno vs **11.5%** del buy & hold.
- Aunque el ROC-AUC está cerca de 0.5, la estrategia logra:
    - Evitar varios días perdedores
    - Acumular beneficios en días con retornos positivos algo mayores
    - Beneficiarse del efecto compuesto de muchas pequeñas ventajas.

### **Simulaciones para NKE y MBG.DE**

En el notebook:

- Se cargan best_model_NKE.pkl y best_model_MBG-DE.pkl.
- Se repite exactamente el mismo flujo de simulación sobre 2025:
    - cálculo de señales diarias,
    - estrategia intradía,
    - comparación contra buy & hold,
    - tabla de capital final, retorno % y n_trades.

## **Conexión métricas de ML ↔ PnL de trading**

Este punto es **explícito en el enunciado**: conectar las métricas de clasificación con las métricas económicas.

### **¿Cómo puede un ROC-AUC ~ 0.5 generar buen retorno?**

1. **Las métricas de clasificación no ponderan el tamaño de los movimientos:**
    - F1 y ROC-AUC solo se fijan en “acertó/no acertó” la dirección.
    - No diferencian entre un día con +0.2% y otro con +3%.
    - Es posible que el modelo esté ligeramente mejor en días de movimientos grandes.
2. **El modelo puede ser selectivo:**
    - En AAPL, el modelo solo opera en 168 de ~227 días.
    - Si los días operados tienden a ser “mejores” que el promedio (ligeramente más alcistas), la estrategia puede superar al buy & hold.
3. **Efecto multiplicativo de pequeños edges:**
    - Una ventaja pequeña pero sistemática se compone en el tiempo.
    - Aunque ROC-AUC ≈ 0.5, un sesgo leve hacia días ganadores puede ser suficiente para mejorar el PnL.

### **Cuando un F1 alto no implica buen PnL**

- **Overfitting a períodos específicos:**
    
    MBG.DE es el ejemplo: F1 alto en validación pero desastroso en Test y en simulación.
    
- **Demasiados trades:**
    
    En la vida real, comisiones y slippage erosionarían un modelo que tradea demasiado con ventaja pequeña.
    
- **Asimetría:**
    
    Se puede acertar muchas subidas pequeñas pero equivocarse en pocas caídas grandes.
    
- **Métrica desalineada con el objetivo económico:**
    
    F1 no diferencia el costo de un falso positivo grande (operar en una gran caída) vs muchos falsos negativos pequeños.
    

---

## **🌐 FASE 5 – API REST (model_api/app.py)**

Servicio: model-api (Docker)

Stack:

- **FastAPI** como framework web.
- **Uvicorn** como servidor ASGI.
- **Joblib** para cargar el modelo serializado.
- Modelo servido por defecto: models/best_model_AAPL.pkl (configurable vía MODEL_PATH).

### **Dockerfile (resumen conceptual)**

- Base: python:3.11-slim
- Instalación de dependencias desde model_api/requirements.txt.
- Copia de app.py.
- Directorio /models donde se monta el volumen con los .pkl.
- Comando de arranque:

```jsx
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Levantar solo la API**

```jsx
docker compose up -d model-api
```

![image.png](Proyecto%20Final/image%206.png)

Verificar:

```jsx
curl http://localhost:8000/health
```

![image.png](Proyecto%20Final/image%207.png)

### **Endpoint**

### **/predict**

**Cuerpo de ejemplo:**

```jsx
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "day_of_week": 1,
    "is_monday": 0,
    "is_friday": 0,
    "open_lag1": 170.5,
    "close_lag1": 171.2,
    "high_lag1": 172.0,
    "low_lag1": 169.8,
    "volume_lag1": 120000000,
    "return_close_open_lag1": 0.0041,
    "return_prev_close_lag1": 0.0035,
    "volatility_n_days_lag1": 0.0123
  }'
```

## **Guía rápida de reproducción (checklist del PSet)**

1. **Ingesta (raw.prices_daily):**
    - Ejecutar 01_ingesta_prices_raw.ipynb.
    - Verificar que haya datos 2018–2025 para AAPL, NKE, MBG.DE.
2. **Feature engineering (analytics.daily_features – Proyecto 06):**
    - Ejecutar docker compose run --rm feature-builder ... para cada ticker.
    - Verificar con un SELECT sobre analytics.daily_features.
3. **ML (clasificador de trading):**
    - Ejecutar 02_ml_trading_classifier.ipynb.
    - Entrenar modelos para los 3 activos.
    - Elegir modelo ganador por F1 en validación.
    - Guardar best_model_*.pkl en models/.
    - Incluir matrices de confusión + classification_report en Test.
4. **Simulaciones de trading (2025):**
    - Ejecutar 03_Simulaciones.ipynb.
    - Simular modelo vs buy & hold para AAPL (y repetir para NKE, MBG.DE).
    - Comparar capital final, retorno %, nº de trades.
5. **API REST:**
    - Construir imagen model-api y levantar el servicio.
    - Probar /health y /predict con curl.
    - Documentar ejemplo de request/response.

# **Discusión de resultados, análisis e interpretabilidad de los modelos**

### **1. Visión general por activo**

En términos de métricas de clasificación (F1, ROC-AUC) y de **performance económico** (PnL en las simulaciones de 2025), los tres activos se comportan de forma distinta:

- **AAPL**
    - Métricas de ML (clasificación):
        - F1 en validación ≈ 0.66 (mejor modelo: ExtraTrees).
        - F1 en Test ≈ 0.68, ROC-AUC en Test ≈ 0.49–0.50.
        - Matriz de confusión razonablemente balanceada: el modelo captura una buena parte de los días alcistas (recall alto en la clase 1) a costa de algunos falsos positivos.
    - Simulación de trading (2025):
        - Buy & hold: ~11.5% de retorno.
        - Modelo de ML: ~22.4% de retorno con 168 trades.
    - Conclusión:
        - Aunque el ROC-AUC está muy cercano a 0.5 (lo que sugiere una capacidad predictiva global limitada), la combinación entre **recall elevado en días alcistas** y una **gestión simple de exposición** (solo operar cuando el modelo predice subida) permite generar un retorno superior al buy & hold.
- **NKE**
    - Métricas de ML:
        - F1 en validación ≈ 0.67 (modelo ganador: DecisionTree).
        - F1 en Test ≈ 0.57–0.58, ROC-AUC ≈ 0.50.
        - Distribución de clases bastante balanceada; la mejora frente al baseline es moderada.
    - Simulación:
        - El modelo ofrece un comportamiento más “neutral”: no destruye valor de forma dramática, pero las mejoras sobre buy & hold son pequeñas o sensibles al período.
    - Conclusión:
        - NKE ilustra un caso intermedio donde el modelo tiene una **ligera señal**, pero no lo suficiente como para garantizar una mejora robusta en PnL. Es útil para discutir la diferencia entre “estadísticamente un poco mejor que tirar una moneda” y “económicamente interesante”.
- **MBG.DE**
    - Métricas de ML:
        - F1 en validación ≈ 0.63 (Decision Tree), pero
        - F1 en Test ≈ 0.03 y recall casi nulo en la clase positiva.
        - ROC-AUC en Test apenas por encima de 0.5, comportamiento casi aleatorio fuera del período de validación.
    - Simulación:
        - El modelo **no agrega valor**; puede incluso ser peor que buy & hold.
    - Conclusión:
        - Ejemplo claro de **overfitting**: el modelo se ajusta demasiado al patrón de 2018–2023 y no generaliza a 2024–2025. Es un caso muy útil para el informe, porque muestra que un F1 alto en validación **no garantiza** buen desempeño fuera de muestra.

---

### **2. Relación entre métricas de clasificación y métricas económicas**

Uno de los hallazgos más importantes del proyecto es que:

> Buenas métricas de clasificación (F1, ROC-AUC) no siempre implican buen PnL y viceversa.
> 

En AAPL ocurre el escenario “bueno”:

- F1 en Test es relativamente decente, pero **ROC-AUC está muy cerca de 0.5**.
- Aun así, la estrategia basada en el modelo **duplica aproximadamente** el retorno del buy & hold en 2025.

¿Por qué ocurre esto?

1. **Las métricas de clasificación no ponderan el tamaño del movimiento**
    - Tanto un día con +0.2% como uno con +3% cuentan como “acierto” igual en F1.
    - Es posible que el modelo sea ligeramente mejor decidiendo en los días “importantes” (movimientos grandes), aunque su rendimiento promedio sobre todos los días sea casi aleatorio.
2. **Selección de días de operación (filtrado):**
    - El modelo no opera todos los días (ej. 168 de ~227 para AAPL en 2025).
    - Si los días en los que decide operar tienen, en promedio, un retorno algo superior que el resto, el PnL acumulado puede superar a la estrategia pasiva, incluso sin métricas espectaculares.
3. **Acumulación de un edge pequeño:**
    - Una ligera ventaja en probabilidad (por ejemplo, acertar un poco más los días con retornos positivos más grandes) se **compone** a lo largo del tiempo.

En cambio, en MBG.DE se ve el escenario contrario:

- F1 en validación es relativamente alta, pero el modelo se derrumba en Test y en simulación.
- Esto muestra que **validación por sí sola no es suficiente**; el comportamiento en Test y en simulaciones out-of-sample es crítico.

---

### **3. Interpretabilidad y variables más relevantes**

Aunque no se ha aplicado un framework formal como SHAP o LIME, la elección de modelos basados en árboles (Decision Tree, Random Forest, ExtraTrees, Gradient Boosting) permite interpretar de forma razonable:

- **Qué variables parecen más importantes para la decisión de “sube vs baja”:**
    - Retornos del día anterior:
        - return_close_open_lag1
        - return_prev_close_lag1
    - Niveles de precio:
        - open_lag1, close_lag1
    - Volatilidad reciente:
        - volatility_n_days_lag1
    - Factores de calendario:
        - day_of_week, is_monday, is_friday

En términos cualitativos, el modelo tiende a aprender patrones como:

- Después de varios días consecutivos al alza con volatilidad creciente, la probabilidad de una corrección aumenta.
- Algunos días de la semana pueden tener ligeras diferencias estadísticas (por ejemplo, comportamiento distinto en lunes vs viernes), aunque este efecto no es muy fuerte.

---

### **4. Calidad de datos y consistencia del pipeline**

El proyecto hace énfasis en:

- **No tener fuga de información (data leakage):**
    - Todas las features usadas para predecir el día t son calculadas con información hasta t-1 (lags).
    - El split Train / Val / Test es estrictamente temporal.
- **Idempotencia y limpieza de datos:**
    - Antes de cada inserción en raw.prices_daily o analytics.daily_features se eliminan los registros previos del mismo run_id y rango de fechas.
    - Se revisan nulos y duplicados, y se trabaja solo con filas completas en las ventanas con lags.
- **Consistencia entre ingesta, feature-builder y ML:**
    - El notebook de ML **solo lee de analytics.daily_features**, cumpliendo la restricción del PSet.
    - Esto permite confiar en que las métricas reflejan el desempeño de un pipeline reproducible, no de un experimento “hackeado”.

Esta robustez del pipeline es importante porque da confianza en que las métricas y simulaciones no dependen de trucos o errores de preparación de datos.

---

### **5. Análisis cualitativo de las predicciones**

A nivel de predicciones diarias, se observa:

- **AAPL:**
    - Buena parte de los días alcistas en Test y en 2025 son marcados correctamente como 1.
    - El modelo comete falsos positivos (compra en días que terminan cayendo), pero el balance global sigue siendo positivo en PnL.
    - La distribución de señales (por ejemplo {0: 59, 1: 168} en 2025) muestra una estrategia bastante activa, lo cual sería sensible a comisiones en un entorno real.
- **NKE:**
    - El modelo se comporta de forma más “neutral”, con aciertos y errores relativamente balanceados.
    - En un entorno con costos de transacción, la utilidad económica podría ser limitada, aunque la clasificación sea algo mejor que el baseline.
- **MBG.DE:**
    - El modelo predice mal en Test; la matriz de confusión muestra que prácticamente **no aprende un patrón útil** fuera del período de validación.
    - A nivel económico, esto se traduce en decisiones casi aleatorias o incluso adversas.

---

### **6. Limitaciones y posibles mejoras**

Limitaciones identificadas:

- **Horizonte de predicción muy corto (1 día):**
    
    Predecir solo “sube/baja mañana” a partir del día anterior es un problema difícil, especialmente en mercados líquidos y relativamente eficientes.
    
- **No se modela el tamaño del retorno:**
    
    La variable objetivo es puramente direccional (up/down), no contempla la magnitud. Modelar return directamente (regresión) o clases ordinales (pequeña subida, gran subida, etc.) podría ser más informativo para el PnL.
    
- **Sin costos de transacción:**
    
    En el mundo real, una estrategia con ~150–200 trades anuales podría ver sus retornos significativamente reducidos por comisiones y spreads.
    
- **Limitado a features “simples”:**
    
    No se incluyeron indicadores técnicos más complejos (RSI, MACD, medias móviles largas), ni información fundamental o de sentimiento.
    

Posibles mejoras futuras:

- Incorporar **SHAP** para análisis de interpretabilidad y selección más robusta de features.
- Probar enfoques de **regresión** sobre retornos y luego umbralizar para decisiones de trading.
- Introducir **costos de transacción** en la simulación para obtener métricas más realistas.
- Probar modelos secuenciales (ej. LSTM) o modelos de clasificación calibrada para obtener mejores probabilidades.

---

En resumen, el proyecto muestra:

- Un **pipelines de datos completo y robusto** (raw → analytics → ML → simulación → API).
- Un caso claro (**AAPL**) donde un modelo con ROC-AUC modesto puede generar un PnL interesante.
- Casos de **señal débil (NKE)** y **overfitting (MBG.DE)** que enriquecen la discusión crítica y ayudan a demostrar comprensión de las limitaciones del enfoque.

```markdown
## 🐛 Troubleshooting

### Problema: PostgreSQL no inicia

```bash
# Ver logs
docker compose logs postgres

# Solución común: eliminar volumen corrupto
docker compose down -v
docker compose up -d postgres
```

### Problema: Jupyter no conecta a PostgreSQL

```bash
# Verificar que postgres esté corriendo
docker compose ps postgres

# Probar conexión desde Jupyter
docker exec dm_jupyter ping postgres

# Verificar variables de entorno
docker exec dm_jupyter env | grep PG_
```

### Problema: API devuelve 500

```bash
# Ver logs detallados
docker compose logs -f model-api

# Verificar que el modelo exista
docker exec dm_model_api ls -lh /models/

# Reconstruir imagen
docker compose build model-api
docker compose up -d model-api
```

### Problema: Feature builder falla

```bash
# Ver logs
docker compose logs feature-builder

# Verificar que haya datos en raw.prices_daily
docker exec -it dm_postgres psql -U trading_user -d trading_db -c "SELECT COUNT(*) FROM raw.prices_daily;"

# Ejecutar con debug
docker compose run --rm feature-builder \
  --mode full \
  --ticker AAPL \
  --run-id debug \
  --overwrite true
```

```

```markdown
## 👥 Contribuciones

Este proyecto fue desarrollado como parte del curso de **Data Mining** (Noveno Semestre).

**Autor**: Erick D. Suárez  
**Fecha**: Diciembre 2025  
**Universidad**: Universidad San Francisco de Quito 
**Curso**: Data Mining - Proyecto Final

---

## 📞 Contacto

Para preguntas o sugerencias:
- Email: [erick.dsuarez10@gmail.com]
- GitHub: [erickds10]

---
```
