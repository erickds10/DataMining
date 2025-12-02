# src/build_features.py

import os
import argparse
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text


def get_engine():
    """Construye un engine de SQLAlchemy usando variables de entorno."""
    PG_HOST = os.getenv("PG_HOST", "postgres")
    PG_PORT = os.getenv("PG_PORT", "5432")
    PG_DB = os.getenv("PG_DB", "trading_db")
    PG_USER = os.getenv("PG_USER", "trading_user")
    PG_PASSWORD = os.getenv("PG_PASSWORD", "trading_pass")

    url = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    return create_engine(url)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Feature builder para analytics.daily_features"
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=["full", "by-date-range"],
        required=True,
        help="Modo de ejecución: 'full' usa todo el rango disponible; "
             "'by-date-range' usa start-date y end-date.",
    )
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="Ticker a procesar (ej: AAPL, NKE, MBG.DE).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        required=False,
        help="Fecha inicio (YYYY-MM-DD) para by-date-range.",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        required=False,
        help="Fecha fin (YYYY-MM-DD) para by-date-range.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        required=True,
        help="Identificador lógico de esta corrida de features.",
    )
    parser.add_argument(
        "--overwrite",
        type=str,
        choices=["true", "false"],
        default="true",
        help="Si 'true', borra primero el rango en analytics.daily_features "
             "para este ticker antes de insertar (idempotencia).",
    )

    args = parser.parse_args()
    return args


def load_raw_prices(engine, ticker, mode, start_date, end_date):
    """Lee datos desde raw.prices_daily según modo y rango."""
    if mode == "by-date-range":
        if not start_date or not end_date:
            raise ValueError(
                "En mode=by-date-range debes especificar --start-date y --end-date"
            )
        start = start_date
        end = end_date

    else:  # mode == "full"
        # Detectar rango automáticamente desde raw.prices_daily
        q_range = text("""
            SELECT MIN(date) AS min_date, MAX(date) AS max_date
            FROM raw.prices_daily
            WHERE ticker = :ticker
        """)
        with engine.begin() as conn:
            row = conn.execute(q_range, {"ticker": ticker}).mappings().first()
        if not row or row["min_date"] is None:
            raise ValueError(f"No hay datos en raw.prices_daily para ticker={ticker}")
        start = row["min_date"].strftime("%Y-%m-%d")
        end = row["max_date"].strftime("%Y-%m-%d")

    query = f"""
        SELECT
            date,
            ticker,
            open,
            high,
            low,
            close,
            adj_close,
            volume
        FROM raw.prices_daily
        WHERE ticker = :ticker
          AND date BETWEEN :start AND :end
        ORDER BY date ASC
    """

    df = pd.read_sql(
        text(query),
        engine,
        params={"ticker": ticker, "start": start, "end": end},
    )

    if df.empty:
        raise ValueError(
            f"Sin datos en raw.prices_daily para ticker={ticker}, "
            f"rango={start} → {end}"
        )

    # Asegurar tipo datetime para manejo de fechas
    df["date"] = pd.to_datetime(df["date"])
    print(
        f"Leídos {len(df)} registros de raw.prices_daily para {ticker} "
        f"en rango {df['date'].min().date()} → {df['date'].max().date()}"
    )

    return df, start, end


def build_features(df_raw, run_id, window_volatility=10):
    """Construye el DataFrame de features a partir del raw."""
    df = df_raw.copy()

    # Campos de calendario
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    # Monday=0, Sunday=6 (convención de pandas)
    df["day_of_week"] = df["date"].dt.dayofweek

    # Features de mercado
    df["return_close_open"] = (df["close"] - df["open"]) / df["open"]

    # Retorno contra el cierre anterior (por ticker, aunque acá es un solo ticker)
    df["return_prev_close"] = df["close"].pct_change()  # close / close_lag1 - 1

    # Volatilidad rolling (std) de return_prev_close
    df["volatility_n_days"] = (
        df["return_prev_close"]
        .rolling(window=window_volatility, min_periods=window_volatility)
        .std()
    )

    # Flags
    df["is_monday"] = df["day_of_week"] == 0
    df["is_friday"] = df["day_of_week"] == 4

    # Metadatos
    df["run_id"] = run_id
    df["ingested_at_utc"] = pd.Timestamp.utcnow()

    # Seleccionar columnas finales en el orden esperado
    df_features = df[
        [
            "date",
            "ticker",
            "year",
            "month",
            "day_of_week",
            "open",
            "close",
            "high",
            "low",
            "volume",
            "return_close_open",
            "return_prev_close",
            "volatility_n_days",
            "is_monday",
            "is_friday",
            "run_id",
            "ingested_at_utc",
        ]
    ].copy()

    # Convertir date a solo fecha (sin hora)
    df_features["date"] = df_features["date"].dt.date

    print(
        f"Construidas features para {len(df_features)} filas. "
        f"Rango {df_features['date'].min()} → {df_features['date'].max()}"
    )

    return df_features


def upsert_features(engine, df_features, ticker, start, end, overwrite=True):
    """Inserta en analytics.daily_features con idempotencia."""
    print(
        f"\nUpsert en analytics.daily_features para ticker={ticker}, "
        f"rango={start} → {end}, overwrite={overwrite}"
    )

    start_date = df_features["date"].min()
    end_date = df_features["date"].max()

    if overwrite:
        delete_sql = text("""
            DELETE FROM analytics.daily_features
            WHERE ticker = :ticker
              AND date BETWEEN :start_date AND :end_date
        """)
        with engine.begin() as conn:
            conn.execute(
                delete_sql,
                {
                    "ticker": ticker,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
        print("Filas previas eliminadas (si existían).")

    # Insertar
    df_features.to_sql(
        "daily_features",
        con=engine,
        schema="analytics",
        if_exists="append",
        index=False,
    )

    print("Inserción completada en analytics.daily_features ✅")


def main():
    args = parse_args()
    engine = get_engine()

    overwrite = args.overwrite.lower() == "true"

    print(f"\n=== Feature Builder ===")
    print(f"Modo: {args.mode}")
    print(f"Ticker: {args.ticker}")
    print(f"Start-date (param): {args.start_date}")
    print(f"End-date (param): {args.end_date}")
    print(f"Run ID: {args.run_id}")
    print(f"Overwrite: {overwrite}")

    df_raw, start, end = load_raw_prices(
        engine,
        ticker=args.ticker,
        mode=args.mode,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    df_features = build_features(
        df_raw,
        run_id=args.run_id,
        window_volatility=10,
    )

    upsert_features(
        engine,
        df_features,
        ticker=args.ticker,
        start=start,
        end=end,
        overwrite=overwrite,
    )

    # Resumen final desde la tabla analytics.daily_features
    summary_sql = text("""
        SELECT
            ticker,
            COUNT(*) AS n_rows,
            MIN(date) AS min_date,
            MAX(date) AS max_date
        FROM analytics.daily_features
        WHERE ticker = :ticker
        GROUP BY ticker
    """)
    with engine.begin() as conn:
        row = conn.execute(summary_sql, {"ticker": args.ticker}).mappings().first()

    if row:
        print(
            f"\nResumen en analytics.daily_features para {args.ticker}: "
            f"n_rows={row['n_rows']}, "
            f"min_date={row['min_date']}, "
            f"max_date={row['max_date']}"
        )
    else:
        print(f"\n⚠️ No se encontraron filas en analytics.daily_features para {args.ticker}")


if __name__ == "__main__":
    main()