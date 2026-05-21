from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.auth import require_auth
from apps.api.settings import settings
from db.models import Asset

router = APIRouter(prefix="/assets", tags=["assets"], dependencies=[Depends(require_auth)])


@router.get("/{asset_id}")
def get_asset(asset_id: str, token: str | None = Query(None), db: Session = Depends(get_db)):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    p = Path(asset.uri)
    if not p.exists():
        raise HTTPException(status_code=404, detail="Asset file not found on disk")

    # Prevent path traversal: asset must live under data_dir
    base = Path(settings.data_dir).resolve()
    rp = p.resolve()
    if base not in rp.parents and rp != base:
        raise HTTPException(status_code=403, detail="Invalid asset path")

    return FileResponse(str(rp), filename=rp.name)
