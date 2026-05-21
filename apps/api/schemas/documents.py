from __future__ import annotations

from pydantic import BaseModel, Field


class UploadDocumentResponse(BaseModel):
    document_id: str
    sha256: str
    filename: str


class CreatePromptDocumentRequest(BaseModel):
    title: str | None = Field(default=None, description="Optional title shown in the UI")
    text: str = Field(min_length=1, description="Plain text prompt / notes")


class CreatePromptDocumentResponse(BaseModel):
    document_id: str
    sha256: str
    filename: str