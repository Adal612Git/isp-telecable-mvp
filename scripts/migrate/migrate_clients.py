#!/usr/bin/env python3
import csv, sys, os
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: migrate_clients.py <input.csv>")
        sys.exit(2)
    inp = Path(sys.argv[1])
    out_dir = Path('Tests/reports/migracion')
    out_dir.mkdir(parents=True, exist_ok=True)
    rej = out_dir / 'rechazos.csv'
    res = out_dir / 'resumen.csv'
    ok = 0; bad = 0
    with inp.open() as f, rej.open('w', newline='') as rf:
        r = csv.DictReader(f)
        rw = csv.writer(rf)
        rw.writerow(['row','motivo'])
        for i,row in enumerate(r, start=1):
            if not row.get('rfc') or not row.get('email'):
                rw.writerow([i, 'faltan rfc/email'])
                bad += 1; continue
            ok += 1
    with res.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['total','ok','rechazados'])
        w.writerow([ok+bad, ok, bad])
    print(f"Wrote {rej} and {res}")

if __name__ == '__main__':
    main()
