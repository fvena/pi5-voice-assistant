"""Configuration from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from .env file."""

    # LLM
    MODEL_PATH: str = os.getenv("MODEL_PATH", "./models/Qwen_Qwen3-1.7B-Q4_K_M.gguf")
    N_THREADS: int = int(os.getenv("N_THREADS", "3"))
    N_CTX: int = int(os.getenv("N_CTX", "2048"))
    N_BATCH: int = int(os.getenv("N_BATCH", "256"))
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "256"))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))

    # ASR
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    WHISPER_LANGUAGE: str = os.getenv("WHISPER_LANGUAGE", "es")

    # TTS
    PIPER_VOICE: str = os.getenv("PIPER_VOICE", "./voices/es_ES-davefx-medium.onnx")

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))

    # History
    MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "10"))
    HISTORY_FILE: str = os.getenv("HISTORY_FILE", "./conversation_history.json")

    # Pipelines — comma-separated list of pipeline names to activate.
    # Empty string means no pipelines loaded (server starts with /health only).
    # Example: PIPELINES=robot,assistant
    PIPELINES: str = os.getenv("PIPELINES", "")


settings = Settings()
