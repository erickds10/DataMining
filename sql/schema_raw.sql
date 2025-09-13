-- Crear esquema raw
CREATE SCHEMA IF NOT EXISTS raw;

-- Tabla de Invoices
CREATE TABLE IF NOT EXISTS raw.qb_invoices (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    extract_window_start_utc TIMESTAMPTZ NOT NULL,
    extract_window_end_utc TIMESTAMPTZ NOT NULL,
    page_number INT,
    page_size INT,
    request_payload JSONB
);

-- Tabla de Customers
CREATE TABLE IF NOT EXISTS raw.qb_customers (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    extract_window_start_utc TIMESTAMPTZ NOT NULL,
    extract_window_end_utc TIMESTAMPTZ NOT NULL,
    page_number INT,
    page_size INT,
    request_payload JSONB
);

-- Tabla de Items
CREATE TABLE IF NOT EXISTS raw.qb_items (
    id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    ingested_at_utc TIMESTAMPTZ NOT NULL DEFAULT now(),
    extract_window_start_utc TIMESTAMPTZ NOT NULL,
    extract_window_end_utc TIMESTAMPTZ NOT NULL,
    page_number INT,
    page_size INT,
    request_payload JSONB
);
