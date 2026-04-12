from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from app.services.paper_checker import process_paper, fix_paper
from app.services.stats_store import read_stats
import os

router = APIRouter()


@router.get("/stats/")
async def get_stats():
    return JSONResponse(content=read_stats())


@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")
    if not file.content_type or file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")

    result = process_paper(file)
    return JSONResponse(content=result)


@router.post("/fix/")
async def fix_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")
    if not file.content_type or file.content_type != "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")

    result = fix_paper(file)
    return JSONResponse(content=result)


@router.get("/download/fixed/{filename}")
async def download_fixed(filename: str):
    if not filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 文件")

    fixed_path = os.path.join("./fixed_docs", filename)
    if not os.path.exists(fixed_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(
        fixed_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )