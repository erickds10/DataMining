import requests
from mage_ai.data_preparation.shared.secrets import get_secret_value
from datetime import datetime, timedelta


if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


def refresh_access_token(client_id, client_secret, refresh_token):
    """
    Refresca el access token usando el refresh token de QuickBooks.
    """
    url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

    response = requests.post(url, headers=headers, data=data, auth=(client_id, client_secret))
    response.raise_for_status()
    return response.json()["access_token"]


def _fetch_qb_data(realm_id, access_token, query, base_url, minor_version):
    """
    Ejecuta la query en QuickBooks API con el access token actual.
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
        'Content-Type': 'text/plain'
    }
    params = {'query': query, 'minorversion': minor_version}
    url = f"{base_url.rstrip('/')}/v3/company/{realm_id}/query"

    response = requests.get(url, headers=headers, params=params, timeout=60)
    if response.status_code == 401:
        raise PermissionError("Access token expirado o inválido")
    response.raise_for_status()
    return response.json()


@data_loader
def load_data_from_api(*args, **kwargs):
    """
    Loader para backfill histórico de QBO con segmentación y paginación.
    Parámetros esperados (definir en Variables de la pipeline en Mage):
      - entity: 'invoices' | 'customers' | 'items'
      - fecha_inicio_utc: 'YYYY-MM-DDTHH:MM:SSZ'
      - fecha_fin_utc:    'YYYY-MM-DDTHH:MM:SSZ'
    """
    # Secrets (credenciales sensibles)
    realm_id = get_secret_value('qb_realm_id')
    client_id = get_secret_value('qb_client_id')
    client_secret = get_secret_value('qb_client_secret')
    access_token = get_secret_value('qb_access_token')
    refresh_token = get_secret_value('qb_refresh_token')

    base_url = 'https://sandbox-quickbooks.api.intuit.com'
    minor_version = 75

    # Mapeo correcto de entidades (en singular)
    ENTITY_MAP = {
        'invoices': 'Invoice',
        'customers': 'Customer',
        'items': 'Item',
    }

    entity = kwargs.get('entity', 'invoices').lower()
    entity_qbo = ENTITY_MAP.get(entity, 'Invoice')

    # Fechas desde Variables
    fecha_inicio = datetime.fromisoformat(kwargs['fecha_inicio_utc'].replace('Z', '+00:00'))
    fecha_fin = datetime.fromisoformat(kwargs['fecha_fin_utc'].replace('Z', '+00:00'))

    # Segmentación semanal
    delta = timedelta(weeks=1)
    all_results = []

    while fecha_inicio < fecha_fin:
        tramo_inicio = fecha_inicio
        tramo_fin = min(fecha_inicio + delta, fecha_fin)

        start_pos = 1
        page_size = 1000
        more_pages = True

        while more_pages:
            print(f"Procesando {entity_qbo}: {tramo_inicio.date()} → {tramo_fin.date()}, página {start_pos}")

            # Fechas en formato UTC ISO8601 con sufijo Z
            start_iso = tramo_inicio.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_iso = tramo_fin.strftime("%Y-%m-%dT%H:%M:%SZ")

            query = f"""
            SELECT * FROM {entity_qbo}
            """.strip()

            try:
                data = _fetch_qb_data(realm_id, access_token, query, base_url, minor_version)
            except PermissionError:
                print("Access token expirado. Se procederá a realizar un refesco")
                access_token = refresh_access_token(client_id, client_secret, refresh_token)
                data = _fetch_qb_data(realm_id, access_token, query, base_url, minor_version)

            items = data.get('QueryResponse', {}).get(entity_qbo, [])
            if not items:
                more_pages = False
            else:
                all_results.append({
                    "entity": entity,
                    "fecha_inicio_utc": start_iso,
                    "fecha_fin_utc": end_iso,
                    "page_number": start_pos,
                    "page_size": page_size,
                    "request_payload": query,
                    "response": data
                })
                start_pos += page_size

        fecha_inicio = tramo_fin

    # 🔑 Normalización final: siempre lista
    if isinstance(all_results, dict):
        return [all_results]
    elif not all_results:
        return []
    return all_results


@test
def test_output(*outputs, **kwargs) -> None:
    """
    Verifica que el output sea siempre tratado como lista.
    Mage desempaqueta la lista, así que outputs puede ser una tupla de dicts.
    """
    # Si Mage desempaquetó la lista, outputs será una tupla
    if len(outputs) == 1 and isinstance(outputs[0], list):
        output = outputs[0]
    else:
        # Reconstruir como lista
        output = list(outputs)

    assert isinstance(output, list), f'El output debe ser lista, pero es {type(output)}'

    if len(output) == 0:
        print("Loader ejecutado correctamente pero no devolvió registros (sandbox vacío o rango sin datos).")
    else:
        sample = output[0]
        assert isinstance(sample, dict), f'Cada elemento debe ser dict, pero es {type(sample)}'
        assert "response" in sample, 'Falta la clave \"response\" en el output'
        assert "QueryResponse" in sample["response"], 'La respuesta no contiene \"QueryResponse\"'
