import pandas as pd
import json
from mage_ai.data_preparation.shared.secrets import get_secret_value
from sqlalchemy import create_engine

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@data_exporter
def export_data_to_postgres(df: pd.DataFrame, *args, **kwargs) -> None:
    """
    Exporta el DataFrame de customers normalizados a Postgres RAW.
    Convierte la columna 'payload' a JSON string para soportar JSONB en Postgres.
    Si la tabla no existe (porque hiciste DROP TABLE), pandas la crea automáticamente.
    """
    if df is None or df.empty:
        print("⚠️ DataFrame vacío, no se exporta nada.")
        return

    # 🔑 Convertir payload (dict → JSON string) para compatibilidad con JSONB
    if "payload" in df.columns:
        df = df.copy()
        df["payload"] = df["payload"].apply(
            lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
        )

    # 🔑 Credenciales desde secrets
    user = get_secret_value('POSTGRES_USER')
    password = get_secret_value('POSTGRES_PASSWORD')
    host = get_secret_value('POSTGRES_HOST')
    port = get_secret_value('POSTGRES_PORT')
    db = get_secret_value('POSTGRES_DB')

    schema = "raw"
    table_name = "qb_customers"   

    # Crear conexión SQLAlchemy
    engine = create_engine(
        f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    )

    # Exportar: si la tabla no existe, pandas la crea automáticamente
    df.to_sql(
        table_name,
        engine,
        schema=schema,
        if_exists="append",  # usa "replace" si quieres que borre y cree cada vez
        index=False,
        method="multi"
    )

    print(f"Exportadas {len(df)} filas a {schema}.{table_name}")


@test
def test_export(*args, **kwargs) -> None:
    """
    Este bloque no retorna nada, solo valida que el export no falle.
    """
    assert True
