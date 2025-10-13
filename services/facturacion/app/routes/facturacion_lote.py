from fastapi import APIRouter, UploadFile, File, HTTPException

from ..services.facturacion_lote_service import procesar_lote_csv


router = APIRouter()


@router.post("/facturacion/lote")
async def facturacion_lote(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe ser CSV")
    return await procesar_lote_csv(file)

