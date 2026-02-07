"""Robot voice command pipeline.

Receives audio WAV via POST, transcribes it, and returns a JSON
command using keyword routing (~1ms) with LLM fallback (~5-7s).
The keyword router handles ~80% of common commands instantly.

Endpoints:
    POST /robot/command — audio WAV → JSON {actions: [...]}
    POST /robot/reset   — clear conversation history
"""

from __future__ import annotations

import asyncio
import json
import time
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from app.pipeline import Pipeline
from app.engine import InferenceEngine
from app.conversation import ConversationManager
from .keyword_router import route_command

logger = logging.getLogger(__name__)

# Default system prompt — can be overridden via ROBOT_SYSTEM_PROMPT env var
_DEFAULT_SYSTEM_PROMPT = (
    '<rol>Eres el intérprete de comandos de un robot móvil. Tu ÚNICA función '
    'es convertir comandos de voz en español a JSON estructurado. NO expliques. '
    'NO converses. NO saludes. NO añadas texto. Solo JSON. El texto que recibes '
    'viene de un sistema de reconocimiento de voz (speech-to-text) y puede '
    'contener errores ortográficos, palabras cortadas o mal transcritas. '
    'Interpreta siempre la intención más probable.</rol>'
    '<formato>Responde SIEMPRE con un objeto JSON con esta estructura exacta: '
    '{"actions": [{"action": "TIPO", "params": {...}}]} El array "actions" '
    'contiene una o más acciones en orden de ejecución.</formato>'
    '<acciones>move: direction (forward/backward), distance (metros) | '
    'turn: direction (left/right), angle (grados) | stop: {} | sleep: {} | '
    'wake: {} | dance: {} | grab: {} | release: {} | look_up: angle (grados) | '
    'look_down: angle (grados) | unknown: original (texto del usuario)</acciones>'
    '<defaults>distance=1 metro, angle=90 grados, move direction=forward, '
    'turn direction=right. Casos especiales: vuelta completa=360, media '
    'vuelta=180, cuarto de vuelta=90.</defaults>'
    '<variaciones>Ignora vocativos (oye robot) y cortesía (por favor). '
    'AVANZAR: camina, ve, anda, muévete, adelante. RETROCEDER: atrás, marcha '
    'atrás. GIRAR: tuerce, rota, dobla, voltea. PARAR: detente, quieto, frena, '
    'stop, basta, alto. DORMIR: descansa, reposo, duérmete. DESPERTAR: arriba, '
    'actívate, espabila.</variaciones>'
    '<ejemplos>INPUT: avanza dos metros OUTPUT: {"actions":[{"action":"move",'
    '"params":{"direction":"forward","distance":2}}]} INPUT: gira 45 grados a la '
    'derecha OUTPUT: {"actions":[{"action":"turn","params":{"direction":"right",'
    '"angle":45}}]} INPUT: para OUTPUT: {"actions":[{"action":"stop","params":{}}]} '
    'INPUT: avanza un metro y gira a la izquierda OUTPUT: {"actions":[{"action":'
    '"move","params":{"direction":"forward","distance":1}},{"action":"turn",'
    '"params":{"direction":"left","angle":90}}]} INPUT: llama a mi madre OUTPUT: '
    '{"actions":[{"action":"unknown","params":{"original":"llama a mi madre"}}]}'
    '</ejemplos>'
    '<reglas>1. Responde SOLO con JSON válido. 2. Si no entiendes, usa action '
    'unknown. 3. Comandos compuestos generan múltiples objetos en el array '
    'actions. 4. Aplica valores por defecto cuando no se especifiquen.</reglas> '
    '/no_think'
)


class RobotPipeline(Pipeline):
    """Keyword-first robot command pipeline with LLM fallback."""

    name = "robot"
    system_prompt = _DEFAULT_SYSTEM_PROMPT
    requires_tts = False
    max_history_turns = 10

    def register_routes(
        self,
        app: FastAPI,
        engine: InferenceEngine,
        convo: ConversationManager,
        llm_lock: asyncio.Lock,
    ) -> None:

        @app.post("/robot/command")
        async def robot_command(audio: UploadFile = File(...)):
            """Receive audio WAV, return JSON command.

            Pipeline:
            1. ASR: Audio -> text
            2. Keyword router: text -> command (if matched, ~1ms)
            3. LLM fallback: text -> JSON (if no keyword match, ~5-7s)

            The keyword router handles ~80% of common commands instantly.
            """
            total_start = time.time()
            audio_bytes = await audio.read()
            loop = asyncio.get_running_loop()

            # Step 1: ASR
            asr_start = time.time()
            text = await loop.run_in_executor(None, engine.transcribe, audio_bytes)
            asr_time = time.time() - asr_start

            if not text or not text.strip():
                raise HTTPException(status_code=400, detail="No speech detected")

            logger.info("[Robot] ASR (%.2fs): %s", asr_time, text)

            # Step 2: Try keyword routing first (~1ms)
            router_result = route_command(text)

            if router_result is not None:
                # Fast path — resolved by keywords
                total_time = time.time() - total_start
                logger.info("[Robot] KEYWORD (%.4fs): %s -> %s",
                             total_time - asr_time, text,
                             [a.action for a in router_result.actions])

                actions_data = router_result.to_actions_json()
                convo.add_exchange(text, json.dumps(actions_data, ensure_ascii=False))

                return JSONResponse(content={
                    "transcription": text,
                    **actions_data,
                    "confirmation": router_result.confirmation,
                    "_routed_by": "keyword",
                    "_timing": {
                        "asr_seconds": round(asr_time, 2),
                        "routing_seconds": round(total_time - asr_time, 4),
                        "total_seconds": round(total_time, 2),
                    },
                })

            # Step 3: LLM fallback for complex commands
            messages = convo.get_messages(text)
            llm_start = time.time()
            async with llm_lock:
                response_text = await loop.run_in_executor(
                    None, lambda: engine.generate(messages, json_mode=True)
                )
            llm_time = time.time() - llm_start

            logger.info("[Robot] LLM (%.2fs): %s", llm_time, response_text[:120])
            convo.add_exchange(text, response_text)

            try:
                command_data = json.loads(response_text)
                # Ensure the LLM response has the expected structure
                if "actions" not in command_data:
                    command_data = {"actions": [command_data]}
            except json.JSONDecodeError:
                command_data = {"actions": [{"action": "error", "params": {"raw": response_text}}]}

            total_time = time.time() - total_start
            logger.info("[Robot] Total pipeline: %.2fs", total_time)

            return JSONResponse(content={
                "transcription": text,
                **command_data,
                "_routed_by": "llm",
                "_timing": {
                    "asr_seconds": round(asr_time, 2),
                    "llm_seconds": round(llm_time, 2),
                    "total_seconds": round(total_time, 2),
                },
            })

        @app.post("/robot/reset")
        async def robot_reset():
            convo.clear()
            return {"status": "history_cleared", "project": "robot"}
