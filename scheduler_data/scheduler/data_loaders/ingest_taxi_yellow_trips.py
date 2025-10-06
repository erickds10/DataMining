if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test

import pandas as pd
import json

def _to_int(x, default):
    try:
        return int(x)
    except Exception:
        return default

def _coerce_services(val, default=('yellow','green')):
    """
    Acepta lista Python, JSON string '["yellow","green"]', o 'yellow,green'
    y devuelve lista normalizada en minúsculas.
    """
    if val is None:
        return [s.lower() for s in default]
    if isinstance(val, (list, tuple)):
        return [str(s).lower().strip() for s in val]
    if isinstance(val, str):
        val = val.strip()
        # intenta JSON
        try:
            parsed = json.loads(val)
            if isinstance(parsed, (list, tuple)):
                return [str(s).lower().strip() for s in parsed]
        except Exception:
            pass
        # intenta CSV
        return [s.strip().lower() for s in val.split(',') if s.strip()]
    return [str(val).lower().strip()]

def _coerce_months(val):
    """
    Acepta lista/tupla, JSON string '[1,2,3]' o CSV '1,2,3'.
    Si es None -> 1..12
    """
    if val is None:
        return list(range(1, 13))
    if isinstance(val, (list, tuple)):
        return [int(m) for m in val]
    if isinstance(val, str):
        val = val.strip()
        try:
            parsed = json.loads(val)
            if isinstance(parsed, (list, tuple)):
                return [int(m) for m in parsed]
        except Exception:
            pass
        return [int(m.strip()) for m in val.split(',') if m.strip()]
    # fallback
    return list(range(1, 13))

@data_loader
def load_data(*args, **kwargs):
    """
    Genera un 'manifest' con (service, year, month, url) sin cargar datos a RAM.
    Lee parámetros desde Variables del pipeline (kwargs) o usa defaults.
    """
    year_from = _to_int(kwargs.get('year_from', 2019), 2019)
    year_to   = _to_int(kwargs.get('year_to',   2019), 2019)
    services  = _coerce_services(kwargs.get('services', ('yellow','green')))
    months    = _coerce_months(kwargs.get('months'))

    base = 'https://d37ci6vzurychx.cloudfront.net/trip-data'
    rows = []
    for y in range(year_from, year_to + 1):
        for m in months:
            for svc in services:
                ym = f'{y:04d}-{m:02d}'
                url = f'{base}/{svc}_tripdata_{ym}.parquet'
                rows.append({'service': svc, 'year': y, 'month': m, 'url': url})

    manifest = pd.DataFrame(rows)
    return manifest

@test
def test_output(output, *args) -> None:
    assert output is not None and len(output) > 0, 'Manifest vacío'
    needed = {'service','year','month','url'}
    assert needed.issubset(output.columns), f'Faltan columnas {needed - set(output.columns)}'
