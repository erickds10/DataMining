if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

@custom
def run(*args, **kwargs):
    import pandas as pd
    from sqlalchemy import create_engine
    from snowflake.sqlalchemy import URL
    from mage_ai.data_preparation.shared.secrets import get_secret_value

    # --- helpers ---
    def require(name):
        v = (get_secret_value(name) or '').strip()
        if not v:
            raise ValueError(f"Falta secret {name}")
        return v

    acct = require('SNOWFLAKE_ACCOUNT')
    user = require('SNOWFLAKE_USER')
    pwd  = require('SNOWFLAKE_PASSWORD')
    role = require('SNOWFLAKE_ROLE')
    wh   = require('SNOWFLAKE_WAREHOUSE')
    db   = require('SNOWFLAKE_DATABASE')
    sch  = (get_secret_value('SNOWFLAKE_SCHEMA_RAW') or 'RAW').strip()

    eng = create_engine(URL(
        account=acct, user=user, password=pwd,
        role=role, warehouse=wh, database=db, schema=sch
    ))

    # Fuente principal (TLC) + fallback (Todd Schneider)
    urls = [
        "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv",
        "https://raw.githubusercontent.com/toddwschneider/nyc-taxi-data/master/taxi_zones/taxi_zone_lookup.csv",
    ]

    last_err = None
    df = None
    chosen = None
    for u in urls:
        try:
            df = pd.read_csv(u)
            chosen = u
            break
        except Exception as e:
            last_err = e

    if df is None:
        raise RuntimeError(f"No pude descargar taxi_zone_lookup de ninguna fuente. Último error: {last_err}")

    # Limpieza mínima
    df.columns = [c.strip() for c in df.columns]
    # Columnas esperadas: LocationID,Borough,Zone,service_zone

    # Escribe en RAW (reemplaza si existía)
    df.to_sql('TAXI_ZONE_LOOKUP', eng, schema=sch, if_exists='replace', index=False)

    print(f"[OK] RAW.TAXI_ZONE_LOOKUP cargada desde: {chosen}")
    print(f"Filas: {len(df)} | Boroughs: {sorted(df['Borough'].dropna().unique().tolist())}")
