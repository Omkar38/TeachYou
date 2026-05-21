from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CaptionStyle(BaseModel):
    style: Literal["off", "minimal", "big_bold", "karaoke"] = "minimal"
    highlight_color: str = "#FFD400"


class Voiceover(BaseModel):
    provider: Literal["openai", "google", "elevenlabs", "cartesia", "espeak"] = "espeak"
    voice_id: str = "en-us"
    speed: float = 1.0


class MediaCandidate(BaseModel):
    source: Literal["pexels", "pixabay", "upload", "generated"] = "generated"
    asset_id: str = ""
    url: str = ""
    thumb_url: str = ""
    duration_s: float = 0.0
    width: int = 0
    height: int = 0


class Scene(BaseModel):
    scene_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int = 0
    style: Literal["whiteboard", "stock_broll", "slide"] = "whiteboard"
    title: str = ""
    objective: str = ""
    script: str = ""
    duration_s: float = 15.0
    voiceover: Voiceover = Field(default_factory=Voiceover)
    media_candidates: list[MediaCandidate] = Field(default_factory=list)
    selected_media_idx: int = 0
    captions: CaptionStyle = Field(default_factory=CaptionStyle)
    music_mood: Optional[Literal["upbeat", "calm", "cinematic", "none"]] = "none"
    music_level: float = 0.2
    transition_in: Literal["cut", "fade", "slide"] = "cut"


class Brand(BaseModel):
    logo_url: str = ""
    primary_color: str = "#8b5cf6"
    font: str = "Inter"


class Storyboard(BaseModel):
    storyboard_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = ""
    title: str = ""
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "9:16"
    length_preset: Literal["15s", "30s", "60s", "3m", "10m"] = "30s"
    brand: Optional[Brand] = None
    scenes: list[Scene] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    version: int = 1


# Maps length_preset -> (n_scenes, duration_s per scene, words per scene)
PRESET_CONFIG: dict[str, tuple[int, float, int]] = {
    "15s": (1, 15.0, 35),
    "30s": (2, 15.0, 35),
    "60s": (4, 15.0, 35),
    "3m":  (8, 22.0, 55),
    "10m": (20, 30.0, 75),
}
