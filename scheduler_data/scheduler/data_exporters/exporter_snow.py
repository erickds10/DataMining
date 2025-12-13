if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter

@data_exporter
def export_data(manifest, *args, **kwargs):
    import math, time
    from datetime import datetime
    import pandas as pd, fsspec, pyarrow.parquet as pq
    from sqlalchemy import create_engine, text
    from snowflake.sqlalchemy import URL
    from mage_ai.data_preparation.shared.secrets import get_secret_value

    # ===== Helpers / Secrets =====
    def require(name):
        v = get_secret_value(name)
        if not v or str(v).strip() == '':
            raise ValueError(f"Falta secret {name}")
        return str(v).strip()

    acct = require('SNOWFLAKE_ACCOUNT')
    user = require('SNOWFLAKE_USER')
    pwd  = require('SNOWFLAKE_PASSWORD')
    role = require('SNOWFLAKE_ROLE')
    wh   = require('SNOWFLAKE_WAREHOUSE')
    db   = require('SNOWFLAKE_DATABASE')
    sch  = (get_secret_value('SNOWFLAKE_SCHEMA_RAW') or 'RAW').strip()

    batch_rows = int(kwargs.get('batch_rows', 250_000))
    single_tbl = str(kwargs.get('raw_single_table', 'false')).lower() == 'true'
    single_name = 'TLC_TRIPS_RAW'  # nombre cuando se usa tabla única

    # ===== Conexión y contexto (tolerante) =====
    eng = create_engine(URL(
        account=acct, user=user, password=pwd,
        role=role, warehouse=wh, database=db, schema=sch
    ))

    with eng.begin() as c:
        for cmd, val in [('ROLE', role), ('WAREHOUSE', wh), ('DATABASE', db), ('SCHEMA', sch)]:
            try:
                c.execute(text(f'USE {cmd} {val}'))
            except Exception as e:
                print(f"[WARN] USE {cmd} {val} falló: {e}")
        r = c.execute(text(
            "select current_role(), current_warehouse(), current_database(), current_schema()"
        )).fetchone()
        print(f"[CTX] role={r[0]}, wh={r[1]}, db={r[2]}, sch={r[3]}")

    fq = lambda name: f'{db}.{sch}.{name}'  # nombre totalmente calificado (solo para SQL manual)

    # ===== Auditoría: crear si no existe + auto-migrar columnas =====
    ddl_base = f"""
    CREATE TABLE IF NOT EXISTS {fq('LOAD_AUDIT')}(
      RUN_TS_UTC   TIMESTAMP_NTZ,
      SERVICE_TYPE STRING,
      YEAR         NUMBER,
      MONTH        NUMBER,
      SOURCE_URL   STRING,
      ROWS_LOADED  NUMBER,
      STATUS       STRING,
      ERROR_MSG    STRING
    )
    """
    with eng.begin() as c:
        c.execute(text(ddl_base))
        c.execute(text(f"ALTER TABLE {fq('LOAD_AUDIT')} ADD COLUMN IF NOT EXISTS TARGET_TABLE STRING"))
        c.execute(text(f"ALTER TABLE {fq('LOAD_AUDIT')} ADD COLUMN IF NOT EXISTS CHUNKS NUMBER"))
        c.execute(text(f"ALTER TABLE {fq('LOAD_AUDIT')} ADD COLUMN IF NOT EXISTS ELAPSED_SEC NUMBER"))

    n_total = len(manifest)
    print(f"[START] Archivos en manifest: {n_total} | batch_rows={batch_rows:,} | single_tbl={single_tbl}")

    # ===== Loop de archivos =====
    for i, r in enumerate(manifest.itertuples(index=False), start=1):
        svc = str(r.service).lower()
        y   = int(r.year)
        m   = int(r.month)
        url = str(r.url)
        tbl = single_name if single_tbl else f"TLC_{svc.upper()}_TRIPS_{y}_{m:02d}"  # <-- nombre simple
        mode_first = 'append' if single_tbl else 'replace'  # primera escritura

        print(f"\n[{i}/{n_total}] {svc} {y}-{m:02d}")
        print(f"  URL: {url}")
        print(f"  Destino: {fq(tbl)}")

        t0 = time.time()
        rows_file = 0
        chunk_idx = 0
        est_chunks = None
        started_ts = datetime.utcnow()  # naive para TIMESTAMP_NTZ

        # Auditoría: STARTED
        with eng.begin() as c:
            c.execute(
                text(f"""INSERT INTO {fq('LOAD_AUDIT')}
                         (RUN_TS_UTC,SERVICE_TYPE,YEAR,MONTH,SOURCE_URL,TARGET_TABLE,ROWS_LOADED,CHUNKS,STATUS,ERROR_MSG,ELAPSED_SEC)
                         VALUES(:ts,:svc,:y,:m,:url,:tbl,NULL,NULL,'STARTED',NULL,NULL)"""),
                dict(ts=started_ts, svc=svc, y=y, m=m, url=url, tbl=fq(tbl))
            )

        try:
            with fsspec.open(url, 'rb') as f:
                pf = pq.ParquetFile(f)

                # Estimación por metadata (si disponible)
                try:
                    total_rows_meta = pf.metadata.num_rows
                    est_chunks = math.ceil(total_rows_meta / batch_rows) if total_rows_meta else None
                except Exception:
                    total_rows_meta = None
                    est_chunks = None

                if total_rows_meta is not None:
                    print(f"  Estimado: ~{total_rows_meta:,} filas ≈ {est_chunks or '?'} chunks")

                # Idempotencia fuerte: si vamos a 'replace', dropea explícitamente antes del primer chunk
                if mode_first == 'replace':
                    with eng.begin() as c:
                        c.execute(text(f"DROP TABLE IF EXISTS {fq(tbl)}"))

                last_heartbeat = time.time()

                # ===== Loop de chunks =====
                for batch in pf.iter_batches(batch_size=batch_rows):
                    t_chunk = time.time()
                    df = batch.to_pandas()

                    # Enriquecer con metadata de ingesta (timestamps naive)
                    df['__ingest_ts_utc'] = datetime.utcnow()
                    df['__source_url']    = url
                    df['__service_type']  = svc
                    df['__year']          = y
                    df['__month']         = m

                    # Escritura: usa nombre simple + schema (NO completamente calificado)
                    df.to_sql(
                        name=tbl,
                        con=eng,
                        schema=sch,                     # <-- aquí el schema correcto
                        if_exists=('replace' if (chunk_idx == 0 and mode_first == 'replace') else 'append'),
                        index=False,
                        method='multi',
                        chunksize=16000
                    )

                    n = len(df)
                    rows_file += n
                    chunk_idx += 1
                    dur = time.time() - t_chunk
                    spd = (n / dur) if dur > 0 else 0.0
                    print(f"    · Chunk {chunk_idx}/{est_chunks or '?'} | +{n:,} filas | total={rows_file:,} | {dur:0.2f}s | {spd:,.0f} rows/s")

                    # Heartbeat cada 15s (útil si hay chunks grandes)
                    if time.time() - last_heartbeat > 15:
                        print(f"    · (heartbeat) chunk={chunk_idx} total={rows_file:,}")
                        last_heartbeat = time.time()

            elapsed = time.time() - t0

            # Auditoría: OK
            with eng.begin() as c:
                c.execute(
                    text(f"""UPDATE {fq('LOAD_AUDIT')}
                             SET ROWS_LOADED=:rows, CHUNKS=:ch, STATUS='OK', ERROR_MSG=NULL, ELAPSED_SEC=:sec
                             WHERE RUN_TS_UTC=:ts AND SOURCE_URL=:url AND TARGET_TABLE=:tbl AND STATUS='STARTED'"""),
                    dict(rows=rows_file, ch=chunk_idx, sec=round(elapsed,2),
                         ts=started_ts, url=url, tbl=fq(tbl))
                )
            print(f"[OK] {fq(tbl)}: {rows_file:,} filas en {elapsed:0.2f}s ({(rows_file/elapsed):,.0f} rows/s)")

        except Exception as e:
            elapsed = time.time() - t0
            msg = str(e)[:3000]

            # Auditoría: ERROR (update si había STARTED; si no, insert directo)
            with eng.begin() as c:
                updated = c.execute(
                    text(f"""UPDATE {fq('LOAD_AUDIT')}
                             SET ROWS_LOADED=:rows, CHUNKS=:ch, STATUS='ERROR', ERROR_MSG=:err, ELAPSED_SEC=:sec
                             WHERE RUN_TS_UTC=:ts AND SOURCE_URL=:url AND TARGET_TABLE=:tbl AND STATUS='STARTED'"""),
                    dict(rows=rows_file, ch=chunk_idx, err=msg, sec=round(elapsed,2),
                         ts=started_ts, url=url, tbl=fq(tbl))
                ).rowcount
                if updated == 0:
                    c.execute(
                        text(f"""INSERT INTO {fq('LOAD_AUDIT')}
                                 (RUN_TS_UTC,SERVICE_TYPE,YEAR,MONTH,SOURCE_URL,TARGET_TABLE,ROWS_LOADED,CHUNKS,STATUS,ERROR_MSG,ELAPSED_SEC)
                                 VALUES(:ts,:svc,:y,:m,:url,:tbl,:rows,:ch,'ERROR',:err,:sec)"""),
                        dict(ts=started_ts, svc=svc, y=y, m=m, url=url, tbl=fq(tbl),
                             rows=rows_file, ch=chunk_idx, err=msg, sec=round(elapsed,2))
                    )
            print(f"[ERROR] {fq(tbl)}: {msg}")
            raise
