"""Base class for pluggable voice assistant pipelines.

Each pipeline defines a set of FastAPI endpoints, a system prompt,
and its model requirements. Pipelines are discovered and loaded
dynamically based on the PIPELINES setting in .env.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI
    from .engine import InferenceEngine
    from .conversation import ConversationManager


class Pipeline:
    """Abstract base for a voice assistant pipeline.

    Subclasses must override ``register_routes()`` to add their
    FastAPI endpoints.  The server calls this method once at startup
    after loading the required models.

    Attributes:
        name:              Short identifier (e.g. "robot", "assistant").
        system_prompt:     Default LLM system prompt.  Can be overridden
                           via the ``<NAME>_SYSTEM_PROMPT`` env var.
        requires_tts:      True if any endpoint needs Piper TTS.
        max_history_turns: Conversation history sliding-window size.
    """

    name: str = ""
    system_prompt: str = ""
    requires_tts: bool = False
    max_history_turns: int = 10

    def register_routes(
        self,
        app: FastAPI,
        engine: InferenceEngine,
        convo: ConversationManager,
        llm_lock: asyncio.Lock,
    ) -> None:
        """Register FastAPI endpoints on *app*.

        Args:
            app:      The FastAPI application instance.
            engine:   Shared inference engine (ASR + LLM + TTS).
            convo:    Conversation manager for this pipeline.
            llm_lock: asyncio.Lock that serialises LLM access.
        """
        raise NotImplementedError
