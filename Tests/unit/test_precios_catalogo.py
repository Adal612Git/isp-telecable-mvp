import importlib, os


def test_precio_por_zona(monkeypatch, tmp_path):
    os.environ['DATABASE_URL'] = f"sqlite:///{tmp_path}/test.db"
    db = importlib.import_module('services.catalogo.app.db')
    importlib.reload(db)
    db.init_db()
    main = importlib.import_module('services.catalogo.app.main')
    importlib.reload(main)
    get_planes = main.get_planes


    planes = get_planes()
    assert isinstance(planes, list)
    # with zona NORTE (factor 1.0) vs SUR (1.1) prices differ for FTTH plans
    pn = {p['codigo']: p for p in get_planes(zona='NORTE')}
    ps = {p['codigo']: p for p in get_planes(zona='SUR')}
    assert abs(pn['INT100']['precio'] * 1.1 - ps['INT100']['precio']) < 0.01
