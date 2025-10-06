if 'custom' not in globals():
    from mage_ai.data_preparation.decorators import custom

@custom
def execute(*args, **kwargs):
    from mage_ai.data_preparation.shared.secrets import get_secret_value
    import snowflake.connector as sf

    acct = get_secret_value('SNOWFLAKE_ACCOUNT')
    user = get_secret_value('SNOWFLAKE_USER')
    pwd  = get_secret_value('SNOWFLAKE_PASSWORD')
    wh   = get_secret_value('SNOWFLAKE_WAREHOUSE')
    db   = get_secret_value('SNOWFLAKE_DATABASE')
    sch  = get_secret_value('SNOWFLAKE_SCHEMA_RAW') or 'RAW'
    role = get_secret_value('SNOWFLAKE_ROLE')

    assert all([acct, user, pwd, wh, db, sch, role]), "Faltan secrets"

    # Conecta por el conector nativo (mensaje de error más claro)
    insecure_mode = str(kwargs.get('insecure_mode', 'false')).lower() == 'true'
    conn = sf.connect(
    account=acct, user=user, password=pwd,
    warehouse=wh, database=db, schema=sch, role=role,
    authenticator='snowflake',
    insecure_mode=insecure_mode,
    )


    cur = conn.cursor()
    cur.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_SCHEMA(), CURRENT_ROLE();")
    print(cur.fetchone())
    cur.close()
    conn.close()
    print("Conexión OK ✅")
