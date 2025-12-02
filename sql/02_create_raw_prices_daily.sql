-- Tabla RAW de precios diarios (mercado)
-- Cumple con: date, ticker, OHLCV + metadatos (run_id, ingested_at_utc, source_name)

CREATE TABLE IF NOT EXISTS raw.prices_daily (
    date            DATE            NOT NULL,
    ticker          TEXT            NOT NULL,
    open            DOUBLE PRECISION,
    high            DOUBLE PRECISION,
    low             DOUBLE PRECISION,
    close           DOUBLE PRECISION,
    adj_close       DOUBLE PRECISION,
    volume          BIGINT,
    run_id          TEXT            NOT NULL,
    ingested_at_utc TIMESTAMPTZ     NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC'),
    source_name     TEXT            NOT NULL,
    CONSTRAINT pk_prices_daily PRIMARY KEY (date, ticker, run_id)
);

-- Índice útil para lecturas por ticker y rango de fechas
CREATE INDEX IF NOT EXISTS idx_prices_daily_ticker_date
    ON raw.prices_daily (ticker, date);