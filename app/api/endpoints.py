from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from app.services.paper_checker import process_paper

router = APIRouter()

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