"""Unified voice assistant server with pluggable pipelines.

Pipelines are loaded dynamically based on the PIPELINES setting
in .env.  Each pipeline registers its own FastAPI endpoints and
declares its model requirements (e.g. TTS).  The server only
loads the models that the active pipelines actually need.

Set PIPELINES=robot,assistant to load both, PIPELINES=robot for
robot-only, or leave empty for a bare /health server.
"""

import asyncio
import importlib
import inspect
import os
import time
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .engine import InferenceEngine
from .conversation import ConversationManager
from .pipeline import Pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Global state ───────────────────────────────────────────
engine = InferenceEngine()

# asyncio.Lock prevents concurrent LLM access while keeping
# the event loop responsive for /health and other endpoints
llm_lock = asyncio.Lock()
start_time = time.time()

# Filled during lifespan — pipeline names that were loaded
loaded_pipeline_names: list[str] = []


def _discover_pipelines(names: list[str]) -> list[Pipeline]:
    """Import pipeline modules and return instantiated Pipeline subclasses."""
    pipelines: list[Pipeline] = []
    for name in names:
        module_path = f"pipelines.{name}.pipeline"
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            logger.error("Pipeline '%s' not found at %s", name, module_path)
            continue

        # Find the Pipeline subclass in the module
        found = False
        for _attr_name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Pipeline) and obj is not Pipeline:
                instance = obj()
                # Allow env var override: <NAME>_SYSTEM_PROMPT
                env_prompt = os.getenv(f"{name.upper()}_SYSTEM_PROMPT")
                if env_prompt:
                    instance.system_prompt = env_prompt
                    logger.info("Pipeline '%s': system prompt overridden from env", name)
                pipelines.append(instance)
                found = True
                break

        if not found:
            logger.error("No Pipeline subclass found in %s", module_path)

    return pipelines


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Discover pipelines, load required models, register routes."""
    global loaded_pipeline_names

    # Parse pipeline names from config
    names = [n.strip() for n in settings.PIPELINES.split(",") if n.strip()]

    if not names:
        logger.info("No pipelines configured (PIPELINES is empty) — "
                     "server will only serve /health")

    # Discover and instantiate pipeline classes
    pipelines = _discover_pipelines(names)

    if pipelines:
        # Determine which models are needed
        requires_tts = any(p.requires_tts for p in pipelines)

        # Load models
        engine.load_all(requires_tts=requires_tts)

        # Register each pipeline's routes
        for pipeline in pipelines:
            convo = ConversationManager(
                name=pipeline.name,
                system_prompt=pipeline.system_prompt,
                max_turns=pipeline.max_history_turns,
                persist_path=settings.HISTORY_FILE,
            )
            pipeline.register_routes(app, engine, convo, llm_lock)
            loaded_pipeline_names.append(pipeline.name)
            logger.info("Pipeline '%s' loaded (tts=%s)",
                        pipeline.name, pipeline.requires_tts)

    logger.info("Server ready on %s:%d — pipelines: %s",
                settings.HOST, settings.PORT,
                loaded_pipeline_names or ["none"])
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Voice Assistant Server",
    version="2.0.0",
    lifespan=lifespan,
)


# ── Health ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Non-blocking health check — responds even during LLM inference."""
    return {
        "status": "ok",
        "models_loaded": engine.is_ready(),
        "uptime_seconds": int(time.time() - start_time),
        "pipelines": loaded_pipeline_names,
        "config": {
            "llm": settings.MODEL_PATH.split("/")[-1],
            "whisper": settings.WHISPER_MODEL,
            "tts": settings.PIPER_VOICE.split("/")[-1] if engine.tts_loaded else "not loaded",
        },
    }
