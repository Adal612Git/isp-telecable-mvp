from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from ..services.facturacion_lote_service import procesar_lote_csv


router = APIRouter()


@router.post("/facturacion/lote")
async def facturacion_lote(
    file: UploadFile = File(...),
    idem: int = Query(default=1, description="1=modo idempotente (upsert), 0=estricto"),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    return await procesar_lote_csv(file, idem=bool(idem))
