import importlib, os


def test_idempotencia_header(tmp_path):
    os.environ['DATABASE_URL'] = f"sqlite:///{tmp_path}/test.db"
    db = importlib.import_module('services.pagos.app.db')
    importlib.reload(db)
    db.init_db()
    main = importlib.import_module('services.pagos.app.main')
    importlib.reload(main)
    body = {"metodo": "spei", "monto": 100.0, "referencia": "REF-123"}
    r1 = main.procesar_pago(body, idempotency_key="IDE-1")
    r2 = main.procesar_pago(body, idempotency_key="IDE-1")
    assert r1['referencia'] == r2['referencia']
