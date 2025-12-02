-- Tabla de features diarias "One Big Table"
-- 1 fila = 1 día bursátil por activo
-- Incluye identificación, mercado, derivadas y metadatos mínimos

CREATE TABLE IF NOT EXISTS analytics.daily_features (
    date                DATE            NOT NULL,
    ticker              TEXT            NOT NULL,
    year                INTEGER         NOT NULL,
    month               INTEGER         NOT NULL,
    day_of_week         INTEGER         NOT NULL,   -- 0-6 o 1-7 según tu elección consistente

    open                DOUBLE PRECISION,
    close               DOUBLE PRECISION,
    high                DOUBLE PRECISION,
    low                 DOUBLE PRECISION,
    volume              BIGINT,

    return_close_open   DOUBLE PRECISION,           -- (close - open) / open
    return_prev_close   DOUBLE PRECISION,           -- close / close_lag1 - 1
    volatility_n_days   DOUBLE PRECISION,           -- std de retornos últimos N días

    is_monday           BOOLEAN,
    is_friday           BOOLEAN,

    run_id              TEXT            NOT NULL,
    ingested_at_utc     TIMESTAMPTZ     NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),

    CONSTRAINT pk_daily_features PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_daily_features_ticker_date
    ON analytics.daily_features (ticker, date);