import importlib
import os


def test_validacion_evidencias(tmp_path):
    os.environ['DATABASE_URL'] = f"sqlite:///{tmp_path}/test.db"
    m = importlib.import_module('services.instalaciones.app.db')
    importlib.reload(m)
    m.init_db()
    main = importlib.import_module('services.instalaciones.app.main')
    CerrarIn = getattr(main, 'CerrarIn')
    try:
        CerrarIn(evidencias=[], notas="")
        assert False, 'Debe fallar sin evidencias'
    except Exception:
        pass

