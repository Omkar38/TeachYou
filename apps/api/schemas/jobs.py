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
    """POST /jobs request."""
    model_config = ConfigDict(extra="forbid")

    document_id: str
    mode: Literal["quick", "deep"] = Field(default="quick")
    video_style: Literal["education", "business"] = Field(default="education")
    layout: Literal["laptop", "reels", "landscape", "square"] = Field(
        default="reels",
        description="reels=9:16, landscape/laptop=16:9, square=1:1",
    )
    length_preset: Optional[str] = Field(
        default=None,
        description="30s / 60s / 3m / 10m — overrides the mode-derived default.",
    )
    caption_style: Literal["off", "minimal", "big_bold"] = Field(
        default="minimal",
        description="off=no captions, minimal=small white text, big_bold=large yellow text.",
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
    """POST /jobs response — includes storyboard when planning succeeds synchronously."""
    model_config = ConfigDict(extra="ignore")
    job_id: str
    storyboard: Optional[Dict[str, Any]] = None


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


class BrollSearchRequest(BaseModel):
    """POST /jobs/{id}/scenes/{idx}/broll — search for B-roll candidates."""
    model_config = ConfigDict(extra="forbid")
    query: Optional[str] = None  # falls back to scene title if omitted


class SceneStylePatchRequest(BaseModel):
    """PATCH /jobs/{id}/scenes/{idx}/broll — select a candidate or toggle style."""
    model_config = ConfigDict(extra="forbid")
    selected_idx: Optional[int] = None
    style: Optional[Literal["whiteboard", "stock_broll"]] = None


class StoryboardEditRequest(BaseModel):
    """POST /jobs/{id}/edit — Magic Box instruction."""
    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(..., min_length=1, max_length=500)


class StoryboardEditResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    storyboard: Dict[str, Any]
    changes: list[Dict[str, Any]] = Field(default_factory=list)
    explanation: str = ""


# Backward/alternate names to avoid future confusion if other file imports differ
JobCreateRequest = CreateJobRequest
JobResponse = JobStatusResponse
