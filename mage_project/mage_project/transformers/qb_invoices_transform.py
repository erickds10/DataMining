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
        invoices = response.get("QueryResponse", {}).get("Invoice", [])

        for inv in invoices:
            rows.append({
                "entity": entity,
                "fecha_inicio_utc": fecha_inicio,
                "fecha_fin_utc": fecha_fin,
                "page_number": page_number,
                "page_size": page_size,
                "request_payload": request_payload,
                # Campos principales de la factura
                "Id": inv.get("Id"),
                "DocNumber": inv.get("DocNumber"),
                "TxnDate": inv.get("TxnDate"),
                "TotalAmt": inv.get("TotalAmt"),
                "CurrencyRef": inv.get("CurrencyRef", {}).get("value") if inv.get("CurrencyRef") else None,
                "CustomerRef": inv.get("CustomerRef", {}).get("value") if inv.get("CustomerRef") else None,
                # JSON completo de la factura (útil para RAW)
                "payload": inv,
            })

    df = pd.DataFrame(rows)
    return df


@test
def test_output(output, *args) -> None:
    """
    Validaciones mínimas sobre el DataFrame transformado.
    """
    assert output is not None, "El DataFrame está vacío"
    assert isinstance(output, pd.DataFrame), "El output debe ser un DataFrame"
    if len(output) > 0:
        required_cols = ["Id", "DocNumber", "TxnDate", "TotalAmt", "payload"]
        for col in required_cols:
            assert col in output.columns, f"Falta la columna obligatoria {col}"
