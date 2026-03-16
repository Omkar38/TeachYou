# from __future__ import annotations

# import os
# from pathlib import Path
# from typing import Optional

# from pydantic import Field, AliasChoices
# from pydantic_settings import BaseSettings, SettingsConfigDict



# def _in_docker() -> bool:
#     return os.getenv("IN_DOCKER") == "1" or Path("/.dockerenv").exists()


# IN_DOCKER = _in_docker()

# DEFAULT_REDIS_HOST = "redis" if IN_DOCKER else "localhost"
# DEFAULT_POSTGRES_HOST = "postgres" if IN_DOCKER else "localhost"

# DEFAULT_DATA_DIR = "/app/data" if IN_DOCKER else "data"
# DEFAULT_DATABASE_DSN = (
#     f"postgresql+psycopg2://genai:genai@{DEFAULT_POSTGRES_HOST}:5432/genai"
#     if IN_DOCKER
#     else "sqlite:///./data/app.db"
# )

# DEFAULT_REDIS_URL = f"redis://{DEFAULT_REDIS_HOST}:6379/0"
# DEFAULT_CELERY_BROKER_URL = f"redis://{DEFAULT_REDIS_HOST}:6379/1"
# DEFAULT_CELERY_RESULT_BACKEND = f"redis://{DEFAULT_REDIS_HOST}:6379/2"


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#         extra="forbid",
#         case_sensitive=False,  # allow DEV_TOKEN / dev_token etc.
#     )

#     # Core
#     data_dir: str = DEFAULT_DATA_DIR

#     # SQLAlchemy DSN
#     database_dsn: str = DEFAULT_DATABASE_DSN

#     # Redis
#     redis_url: str = DEFAULT_REDIS_URL

#     # Celery
#     celery_broker_url: str = DEFAULT_CELERY_BROKER_URL
#     celery_result_backend: str = DEFAULT_CELERY_RESULT_BACKEND

#     # Visual search policy
#     # - "offline": only extracted PDF figures/pages/generated slides
#     # - "wikimedia": Wikimedia Commons only
#     # - "ddg": DuckDuckGo images only
#     # - "hybrid": Wikimedia first, then DuckDuckGo fallback
#     image_search_provider: str = "hybrid"
#     image_search_max_per_segment: int = 2
#     image_download_timeout_sec: float = 12.0

#     # --- Security ---
#     # Support BOTH env keys:
#     # - DEV_TOKEN (older)
#     # - API_AUTH_TOKEN (newer)
#     api_auth_token: str = Field(
#         default="dev-token",
#         validation_alias=AliasChoices("DEV_TOKEN", "API_AUTH_TOKEN"),
#     )

#     # --- LLM routing ---
#     # Support BOTH env keys:
#     # - LLM_FALLBACK_ORDER (older)
#     # - LLM_PROVIDER_ORDER (newer)
#     llm_provider_order: str = Field(
#         default="gemini,openai,ollama,offline",
#         validation_alias=AliasChoices("LLM_FALLBACK_ORDER", "LLM_PROVIDER_ORDER"),
#     )
#     # Gemini
#     gemini_api_key: str = ""
#     gemini_model: str = "gemini-2.0-flash"

#     # OpenAI
#     openai_api_key: str = ""
#     openai_model: str = "gpt-4o-mini"

#     # Ollama
#     ollama_base_url: str = "http://localhost:11434"
#     ollama_model: str = "gemma:4b"


# settings = Settings()

# apps/api/settings.py
# from __future__ import annotations

# import os
# from pathlib import Path
# from pydantic import Field, AliasChoices
# from pydantic_settings import BaseSettings, SettingsConfigDict

# def _in_docker() -> bool:
#     return os.getenv("IN_DOCKER") == "1" or Path("/.dockerenv").exists()

# IN_DOCKER = _in_docker()

# DEFAULT_REDIS_HOST = "redis" if IN_DOCKER else "localhost"
# DEFAULT_POSTGRES_HOST = "postgres" if IN_DOCKER else "localhost"

# DEFAULT_DATA_DIR = "/app/data" if IN_DOCKER else "data"
# DEFAULT_DATABASE_DSN = (
#     f"postgresql+psycopg2://genai:genai@{DEFAULT_POSTGRES_HOST}:5432/genai"
#     if IN_DOCKER
#     else "sqlite:///./data/app.db"
# )

# DEFAULT_REDIS_URL = f"redis://{DEFAULT_REDIS_HOST}:6379/0"
# DEFAULT_CELERY_BROKER_URL = f"redis://{DEFAULT_REDIS_HOST}:6379/1"
# DEFAULT_CELERY_RESULT_BACKEND = f"redis://{DEFAULT_REDIS_HOST}:6379/2"

# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#         extra="forbid",
#         case_sensitive=False,
#     )

#     data_dir: str = Field(default=DEFAULT_DATA_DIR, validation_alias=AliasChoices("DATA_DIR"))
#     database_dsn: str = Field(default=DEFAULT_DATABASE_DSN, validation_alias=AliasChoices("DATABASE_DSN"))
#     redis_url: str = Field(default=DEFAULT_REDIS_URL, validation_alias=AliasChoices("REDIS_URL"))
#     celery_broker_url: str = Field(default=DEFAULT_CELERY_BROKER_URL, validation_alias=AliasChoices("CELERY_BROKER_URL"))
#     celery_result_backend: str = Field(default=DEFAULT_CELERY_RESULT_BACKEND, validation_alias=AliasChoices("CELERY_RESULT_BACKEND"))

#     # Auth (support both DEV_TOKEN and API_AUTH_TOKEN)
#     api_auth_token: str = Field(default="dev-token", validation_alias=AliasChoices("API_AUTH_TOKEN", "DEV_TOKEN"))

#     # LLM routing (support both names)
#     llm_provider_order: str = Field(
#         default="gemini,openai,ollama,offline",
#         validation_alias=AliasChoices("LLM_PROVIDER_ORDER", "LLM_FALLBACK_ORDER"),
#     )

#     # IMPORTANT: timeout (this is what you need right now)
#     llm_timeout_sec: float = Field(default=120.0, validation_alias=AliasChoices("LLM_TIMEOUT_SEC"))

#     llm_temperature: float = Field(default=0.3, validation_alias=AliasChoices("LLM_TEMPERATURE"))
#     llm_max_output_tokens: int = Field(default=1024, validation_alias=AliasChoices("LLM_MAX_OUTPUT_TOKENS"))

#     gemini_api_key: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEY"))
#     gemini_model: str = Field(default="gemini-2.0-flash", validation_alias=AliasChoices("GEMINI_MODEL"))

#     openai_api_key: str = Field(default="", validation_alias=AliasChoices("OPENAI_API_KEY"))
#     openai_model: str = Field(default="gpt-4o-mini", validation_alias=AliasChoices("OPENAI_MODEL"))

#     ollama_base_url: str = Field(default="http://localhost:11434", validation_alias=AliasChoices("OLLAMA_BASE_URL"))
#     ollama_model: str = Field(default="gemma3:4b", validation_alias=AliasChoices("OLLAMA_MODEL"))

# settings = Settings()

# apps/api/settings.py
from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


def _in_docker() -> bool:
    return os.getenv("IN_DOCKER") == "1" or Path("/.dockerenv").exists()


IN_DOCKER = _in_docker()

DEFAULT_REDIS_HOST = "redis" if IN_DOCKER else "localhost"
DEFAULT_POSTGRES_HOST = "postgres" if IN_DOCKER else "localhost"

DEFAULT_DATA_DIR = "/app/data" if IN_DOCKER else "data"
DEFAULT_DATABASE_DSN = (
    f"postgresql+psycopg2://genai:genai@{DEFAULT_POSTGRES_HOST}:5432/genai"
    if IN_DOCKER
    else "sqlite:///./data/app.db"
)

DEFAULT_REDIS_URL = f"redis://{DEFAULT_REDIS_HOST}:6379/0"
DEFAULT_CELERY_BROKER_URL = f"redis://{DEFAULT_REDIS_HOST}:6379/1"
DEFAULT_CELERY_RESULT_BACKEND = f"redis://{DEFAULT_REDIS_HOST}:6379/2"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        case_sensitive=False,
    )

    # Paths / DB / Redis / Celery
    data_dir: str = Field(default=DEFAULT_DATA_DIR, validation_alias=AliasChoices("DATA_DIR"))
    database_dsn: str = Field(default=DEFAULT_DATABASE_DSN, validation_alias=AliasChoices("DATABASE_DSN", "POSTGRES_DSN"))

    redis_url: str = Field(default=DEFAULT_REDIS_URL, validation_alias=AliasChoices("REDIS_URL"))
    celery_broker_url: str = Field(default=DEFAULT_CELERY_BROKER_URL, validation_alias=AliasChoices("CELERY_BROKER_URL"))
    celery_result_backend: str = Field(default=DEFAULT_CELERY_RESULT_BACKEND, validation_alias=AliasChoices("CELERY_RESULT_BACKEND"))

    # Auth (support both names)
    api_auth_token: str = Field(default="dev-token", validation_alias=AliasChoices("API_AUTH_TOKEN", "DEV_TOKEN"))

    # -------------------------
    # Visual search policy
    # -------------------------
    # pipeline.py expects settings.image_search_provider
    # Options used by your project: offline | wikimedia | ddg | hybrid
    image_search_provider: str = Field(default="hybrid", validation_alias=AliasChoices("IMAGE_SEARCH_PROVIDER"))
    image_search_max_per_segment: int = Field(default=2, validation_alias=AliasChoices("IMAGE_SEARCH_MAX_PER_SEGMENT"))
    image_download_timeout_sec: float = Field(default=12.0, validation_alias=AliasChoices("IMAGE_DOWNLOAD_TIMEOUT_SEC"))

    # -------------------------
    # LLM routing
    # -------------------------
    llm_provider_order: str = Field(
        default="gemini,openai,ollama,offline",
        validation_alias=AliasChoices("LLM_PROVIDER_ORDER", "LLM_FALLBACK_ORDER"),
    )

    llm_timeout_sec: float = Field(default=120.0, validation_alias=AliasChoices("LLM_TIMEOUT_SEC"))
    llm_temperature: float = Field(default=0.3, validation_alias=AliasChoices("LLM_TEMPERATURE"))
    llm_max_output_tokens: int = Field(default=1024, validation_alias=AliasChoices("LLM_MAX_OUTPUT_TOKENS"))

    gemini_api_key: str = Field(default="", validation_alias=AliasChoices("GEMINI_API_KEY"))
    gemini_model: str = Field(default="gemini-2.0-flash", validation_alias=AliasChoices("GEMINI_MODEL"))

    openai_api_key: str = Field(default="", validation_alias=AliasChoices("OPENAI_API_KEY"))
    openai_model: str = Field(default="gpt-4o-mini", validation_alias=AliasChoices("OPENAI_MODEL"))

    # -------------------------
    # TTS routing (OpenAI -> Google -> eSpeak)
    # -------------------------
    tts_provider_order: str = Field(
        default="openai,google,espeak",
        validation_alias=AliasChoices("TTS_PROVIDER_ORDER"),
    )
    tts_timeout_sec: float = Field(default=60.0, validation_alias=AliasChoices("TTS_TIMEOUT_SEC"))

    # OpenAI TTS
    openai_tts_model: str = Field(default="gpt-4o-mini-tts", validation_alias=AliasChoices("OPENAI_TTS_MODEL"))
    openai_tts_voice: str = Field(default="marin", validation_alias=AliasChoices("OPENAI_TTS_VOICE"))

    # Google Cloud TTS
    google_tts_voice_name: str = Field(default="", validation_alias=AliasChoices("GOOGLE_TTS_VOICE_NAME"))
    google_tts_speaking_rate: float = Field(default=1.0, validation_alias=AliasChoices("GOOGLE_TTS_SPEAKING_RATE"))

    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias=AliasChoices("OLLAMA_BASE_URL"))
    ollama_model: str = Field(default="gemma3:4b", validation_alias=AliasChoices("OLLAMA_MODEL"))


settings = Settings()
