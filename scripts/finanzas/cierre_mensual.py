#!/usr/bin/env python3
import os, csv, sys, json
from datetime import datetime
import urllib.request

def http_json(url):
    with urllib.request.urlopen(url, timeout=5) as r:
        if r.status != 200:
            raise urllib.error.HTTPError(url, r.status, "bad status", r.headers, None)
        return json.loads(r.read().decode('utf-8'))

def main():
    # Cargar puertos desde entorno o .env.ports
    env_ports = {}
    if os.path.exists('.env.ports'):
        with open('.env.ports') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                env_ports[k.strip()] = v.strip()
    fact_port = os.environ.get('HOST_FACTURACION_PORT') or env_ports.get('HOST_FACTURACION_PORT') or '8003'
    pagos_port = os.environ.get('HOST_PAGOS_PORT') or env_ports.get('HOST_PAGOS_PORT') or '8004'

    # Intentar varias opciones si hubiera desalineación de puertos
    fact_candidates = [fact_port, '8003', '8002']
    stats = None
    last_err = None
    for p in fact_candidates:
        try:
            stats = http_json(f"http://localhost:{int(p)}/facturacion/stats")
            break
        except Exception as e:
            last_err = e
            continue
    if stats is None and last_err:
        raise last_err
    # Conciliacion pagos (csv dentro de json)
    conc = http_json(f"http://localhost:{int(pagos_port)}/pagos/conciliar")
    csv_text = conc.get('csv','')
    out_dir = 'Tests/reports/finanzas'
    os.makedirs(out_dir, exist_ok=True)
    mes = datetime.utcnow().strftime('%Y%m')
    cierre = os.path.join(out_dir, f'cierre_mes_{mes}.csv')
    with open(cierre,'w',newline='') as f:
        w = csv.writer(f)
        w.writerow(['metric','valor'])
        for k,v in stats.items(): w.writerow([k,v])
    aging = os.path.join(out_dir, 'aging.csv')
    with open(aging,'w',newline='') as f:
        f.write(csv_text)
    print('Wrote', cierre, 'and', aging)

if __name__=='__main__':
    main()
