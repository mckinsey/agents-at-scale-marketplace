from fastapi import FastAPI, Query, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from .s3_client import s3_client
from .config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="File API",
    description="REST API for S3 file operations via VersityGW",
    version="0.1.0",
)

cors_origins = settings.cors_origins.strip()
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()] if cors_origins else []

cors_methods = settings.cors_allow_methods.strip()
allowed_methods = [method.strip() for method in cors_methods.split(",") if method.strip()] if cors_methods else ["*"]

cors_headers = settings.cors_allow_headers.strip()
allowed_headers = [header.strip() for header in cors_headers.split(",") if header.strip()] if cors_headers else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)

if allowed_origins:
    logger.info(f"CORS configured - origins: {allowed_origins}, credentials: {settings.cors_allow_credentials}, methods: {allowed_methods}, headers: {allowed_headers}")
else:
    logger.info("No CORS origins configured - CORS will block all cross-origin requests")


class ListFilesResponse(BaseModel):
    files: List[Dict[str, Any]]
    directories: List[Dict[str, Any]]
    next_token: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/files", response_model=ListFilesResponse)
async def list_files(
    prefix: str = Query("", description="Filter files by prefix"),
    max_keys: int = Query(1000, ge=1, le=1000, description="Maximum number of files to return"),
    continuation_token: Optional[str] = Query(None, description="Continuation token for pagination"),
):
    result = s3_client.list_files(
        prefix=prefix,
        max_keys=max_keys,
        continuation_token=continuation_token,
    )
    return ListFilesResponse(
        files=result.files, directories=result.directories, next_token=result.next_token
    )


@app.delete("/files/{key:path}")
async def delete_file(key: str):
    try:
        s3_client.delete_file(key)
        return {"status": "deleted", "key": key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/directories")
async def delete_directory(prefix: str = Query(..., description="Directory prefix to delete")):
    try:
        result = s3_client.delete_prefix(prefix)
        return {"status": "deleted", "prefix": prefix, "deleted_count": result["deleted_count"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/files")
async def upload_file(
    file: UploadFile = File(...),
    prefix: str = Form(""),
):
    try:
        key = prefix + file.filename if prefix else file.filename
        result = s3_client.upload_file(file.file, key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/files/{key:path}/download")
async def download_file(key: str):
    try:
        file_stream = s3_client.download_file(key)
        filename = key.split("/")[-1]
        return StreamingResponse(
            file_stream,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
