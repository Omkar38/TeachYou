from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


class SegmentStatusItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    segment_index: int
    title: str | None = None
    objective: str | None = None
    status: str
    duration_target_sec: float | None = None


class CreateJobRequest(BaseModel):
    """
    POST /jobs request.
    For v1 we support quick mode (you can keep full in schema if you want later).
    """
    model_config = ConfigDict(extra="forbid")

    document_id: str
    mode: Literal["quick", "deep"] = Field(
        default="quick",
        description="quick=fast 2–3 scene explainer, deep=8–10 scene explainer",
    )

    # V1.5 options
    video_style: Literal["education", "business"] = Field(
        default="education",
        description="Controls visual theme and tone (education vs. business).",
    )
    layout: Literal["laptop", "reels"] = Field(
        default="laptop",
        description="laptop=1280x720 landscape, reels=720x1280 vertical.",
    )


class SegmentEditorState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    script: str | None = None
    script_override: str | None = None
    scenegraph: Dict[str, Any] | None = None
    scenegraph_override: Dict[str, Any] | None = None


class SegmentDetailResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    job_id: str
    segment_index: int
    title: str | None = None
    objective: str | None = None
    status: str
    duration_target_sec: float | None = None
    editor: SegmentEditorState = Field(default_factory=SegmentEditorState)


class SegmentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # "Click on text to edit" — user edits narration/script. If provided, this becomes the override.
    script_override: str | None = None
    # Advanced (optional): user edits scenegraph directly.
    scenegraph_override: Dict[str, Any] | None = None


class CreateJobResponse(BaseModel):
    """POST /jobs response."""
    model_config = ConfigDict(extra="ignore")
    job_id: str


class JobStatusResponse(BaseModel):
    """
    GET /jobs/{job_id} response.
    artifacts: {type: [{id, uri, meta}, ...]}
    """
    model_config = ConfigDict(extra="ignore")

    id: str
    document_id: str
    mode: str
    status: str
    config: Dict[str, Any] = Field(default_factory=dict)
    progress: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    segments: list[SegmentStatusItem] = Field(
        default_factory=list,
        description="Ordered segment list with status/progress",
    )
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class LibraryJobItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    document_id: str
    mode: Optional[str] = None
    filename: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    thumb_asset_id: Optional[str] = None
    video_asset_id: Optional[str] = None
    duration_sec: Optional[float] = None


# Backward/alternate names to avoid future confusion if other file imports differ
JobCreateRequest = CreateJobRequest
JobResponse = JobStatusResponse
