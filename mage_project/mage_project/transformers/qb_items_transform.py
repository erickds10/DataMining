import pandas as pd

if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


@transformer
def transform(data, *args, **kwargs):
    """
    Transforma el output del loader (lista de dicts con metadatos + response)
    en un DataFrame tabular listo para Postgres RAW.
    """

    # 🔑 Normalizar el input para que siempre sea lista de dicts
    if isinstance(data, dict):
        batches = [data]
    elif isinstance(data, list):
        batches = data
    else:
        raise ValueError(f"Formato inesperado de data: {type(data)}")

    rows = []

    for batch in batches:
        entity = batch.get("entity")
        fecha_inicio = batch.get("fecha_inicio_utc")
        fecha_fin = batch.get("fecha_fin_utc")
        page_number = batch.get("page_number")
        page_size = batch.get("page_size")
        request_payload = batch.get("request_payload")

        response = batch.get("response", {})
        items = response.get("QueryResponse", {}).get("Item", [])

        for it in items:
            rows.append({
                "entity": entity,
                "fecha_inicio_utc": fecha_inicio,
                "fecha_fin_utc": fecha_fin,
                "page_number": page_number,
                "page_size": page_size,
                "request_payload": request_payload,
                # Campos principales del Item
                "Id": it.get("Id"),
                "Name": it.get("Name"),
                "FullyQualifiedName": it.get("FullyQualifiedName"),
                "Active": it.get("Active"),
                "Taxable": it.get("Taxable"),
                "UnitPrice": it.get("UnitPrice"),
                "Type": it.get("Type"),
                "IncomeAccountRef": it.get("IncomeAccountRef", {}).get("value") if it.get("IncomeAccountRef") else None,
                # JSON completo del Item (útil para RAW)
                "payload": it,
            })

    df = pd.DataFrame(rows)
    return df


@test
def test_output(output, *args) -> None:
    assert output is not None, "❌ El DataFrame está vacío"
    assert isinstance(output, pd.DataFrame), "❌ El output debe ser un DataFrame"
    if len(output) > 0:
        required_cols = ["Id", "Name", "Type", "payload"]
        for col in required_cols:
            assert col in output.columns, f"❌ Falta la columna obligatoria {col}"
