import csv
import io
import os
import time
from datetime import datetime
from typing import Dict, Any, List

import aiofiles
from fastapi import UploadFile
from opentelemetry import trace
from prometheus_client import Counter
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..logging_conf import configure_logging
from ..models import Factura


service_name = os.getenv("SERVICE_NAME", "facturacion")
logger = configure_logging(service_name)
tracer = trace.get_tracer(__name__)

# Métrica personalizada: suma del tiempo total por ejecución (ms)
FACTURACION_LOTE_TIEMPO_TOTAL_MS = Counter(
    "facturacion_lote_tiempo_total_ms",
    "Tiempo total del procesamiento de lotes en ms",
)


async def procesar_lote_csv(file: UploadFile, idem: bool = True) -> Dict[str, Any]:
    """
    Procesa un CSV con encabezado: cliente_id,plan_id,monto,folio_interno
    - Inserta facturas con estatus 'emitida' por cada registro válido
    - Genera CSV de resultados en /app/exports/facturacion/
    - Retorna resumen JSON
    """
    # Leer contenido del archivo de forma asíncrona
    raw = await file.read()
    text = raw.decode("utf-8")

    reader = csv.DictReader(io.StringIO(text))
    rows: List[Dict[str, str]] = list(reader)

    total_registros = len(rows)
    logger.info(f"[INFO] Procesando lote con {total_registros} registros")

    resultados: List[List[str]] = []
    exitosos = 0
    fallidos = 0
    tiempos_ms_sum = 0.0

    # Preparar DB
    db: Session = SessionLocal()

    # Asegurar carpeta de exportación
    export_dir = "/app/exports/facturacion"
    os.makedirs(export_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_filename = f"lote_{timestamp}.csv"
    out_path = os.path.join(export_dir, out_filename)

    # Procesar con traza
    with tracer.start_as_current_span("facturacion.lote.csv") as span:
        span.set_attribute("batch.size", total_registros)
        try:
            for row in rows:
                t0 = time.perf_counter()
                estatus = "OK"
                detalle = "Emisión simulada exitosa"

                # Validaciones
                try:
                    cliente_id_raw = row.get("cliente_id")
                    plan_id_raw = row.get("plan_id")
                    monto_raw = row.get("monto")
                    folio = (row.get("folio_interno") or "").strip()

                    if not (cliente_id_raw and plan_id_raw and monto_raw and folio):
                        raise ValueError("Campos faltantes")

                    cliente_id = int(cliente_id_raw)
                    plan_id = int(plan_id_raw)  # actualmente no usado para DB
                    monto = float(monto_raw)

                    if monto < 0:
                        raise ValueError("Monto negativo")

                    existing = db.query(Factura).filter(Factura.uuid == folio).first()
                    if existing:
                        if idem:
                            # Idempotente: actualiza registro existente
                            existing.cliente_id = cliente_id
                            existing.total = monto
                            existing.xml_path = f"lotes/{out_filename}"
                            existing.estatus = "emitida"
                            exitosos += 1
                            detalle = "Actualizado (idempotente)"
                        else:
                            # Estricto: no tocar y marcar como duplicado
                            estatus = "DUPLICADO"
                            detalle = "UUID ya existe"
                            fallidos += 1
                    else:
                        fac = Factura(
                            uuid=folio,
                            cliente_id=cliente_id,
                            total=monto,
                            xml_path=f"lotes/{out_filename}",
                            estatus="emitida",
                        )
                        db.add(fac)
                        exitosos += 1
                except Exception as e:  # noqa: BLE001 - error de validación/negocio
                    estatus = "ERROR"
                    detalle = str(e)
                    fallidos += 1

                dt_ms = (time.perf_counter() - t0) * 1000.0
                tiempos_ms_sum += dt_ms
                resultados.append(
                    [
                        folio,
                        row.get("cliente_id", ""),
                        row.get("plan_id", ""),
                        row.get("monto", ""),
                        estatus,
                        detalle,
                        str(int(dt_ms)),
                    ]
                )

            # Commit una sola vez al final para eficiencia
            db.commit()
        finally:
            db.close()

        # Guardar CSV de resultados (asíncrono)
        header = [
            "folio_interno",
            "cliente_id",
            "plan_id",
            "monto",
            "estatus",
            "detalle",
            "tiempo_ms",
        ]

        # Construir CSV en memoria para escribir en bloque
        out_buf = io.StringIO()
        writer = csv.writer(out_buf)
        writer.writerow(header)
        writer.writerows(resultados)
        csv_text = out_buf.getvalue()

        async with aiofiles.open(out_path, "w", encoding="utf-8", newline="") as f:
            await f.write(csv_text)

        total_ms_int = int(tiempos_ms_sum)
        logger.info(f"[INFO] Tiempo total: {total_ms_int} ms")

        # Métrica personalizada
        FACTURACION_LOTE_TIEMPO_TOTAL_MS.inc(total_ms_int)

        # Trazas
        span.set_attribute("batch.tiempo_total_ms", total_ms_int)
        span.set_attribute("batch.exitosos", exitosos)
        span.set_attribute("batch.fallidos", fallidos)

    return {
        "procesados": total_registros,
        "exitosos": exitosos,
        "fallidos": fallidos,
        "tiempo_total_ms": int(tiempos_ms_sum),
        "csv_resultado": out_filename,
    }
