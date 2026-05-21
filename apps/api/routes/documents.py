from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.auth import require_auth
from apps.api.settings import settings
from core.utils.hashing import sha256_bytes
from apps.api.schemas.documents import CreatePromptDocumentRequest, CreatePromptDocumentResponse
from db.models import Document

router = APIRouter(prefix="/documents", tags=["documents"], dependencies=[Depends(require_auth)])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported in v1")

    content = await file.read()
    doc_id = str(uuid.uuid4())
    digest = sha256_bytes(content)

    upload_dir = os.path.join(settings.data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, f"{doc_id}.pdf")
    with open(path, "wb") as f:
        f.write(content)

    doc = Document(id=doc_id, sha256=digest, filename=file.filename, status="UPLOADED")
    db.add(doc)
    db.commit()

    return {"document_id": doc_id, "sha256": digest, "filename": file.filename}


@router.post("/prompt", response_model=CreatePromptDocumentResponse)
def create_prompt_document(payload: CreatePromptDocumentRequest, db: Session = Depends(get_db)):
    # Store prompt as a .txt under uploads/
    content = (payload.text or "").encode("utf-8")
    doc_id = str(uuid.uuid4())
    digest = sha256_bytes(content)

    upload_dir = os.path.join(settings.data_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, f"{doc_id}.txt")
    with open(path, "wb") as f:
        f.write(content)

    filename = (payload.title or "prompt").strip() or "prompt"
    if not filename.lower().endswith(".txt"):
        filename = f"{filename}.txt"

    doc = Document(id=doc_id, sha256=digest, filename=filename, status="UPLOADED")
    db.add(doc)
    db.commit()

    return CreatePromptDocumentResponse(document_id=doc_id, sha256=digest, filename=filename)


@router.get("/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "sha256": doc.sha256,
        "filename": doc.filename,
        "status": doc.status,
        "created_at": doc.created_at,
    }
