# Pipelines

Los pipelines son modulos independientes que registran endpoints en el servidor FastAPI. Cada pipeline define su propio system prompt, sus rutas HTTP y sus requisitos de modelos.

## Pipelines incluidos

| Pipeline | Endpoints | Requiere TTS |
|----------|-----------|--------------|
| `robot` | `/robot/command`, `/robot/reset` | No |
| `assistant` | `/assistant/chat`, `/assistant/chat/stream`, `/assistant/chat/text`, `/assistant/reset` | Si |

## Activar pipelines

En `.env`, configura la variable `PIPELINES` con los nombres separados por comas:

```bash
# Ambos pipelines
PIPELINES=robot,assistant

# Solo robot (no carga Piper TTS, ahorra ~60 MB de RAM)
PIPELINES=robot

# Solo asistente
PIPELINES=assistant

# Ninguno (servidor solo con /health)
PIPELINES=
```

## Sobreescribir el system prompt

Cada pipeline trae un prompt por defecto. Para sobreescribirlo, define la variable `<NOMBRE>_SYSTEM_PROMPT` en `.env`:

```bash
ROBOT_SYSTEM_PROMPT=Tu prompt personalizado aqui
ASSISTANT_SYSTEM_PROMPT=Tu prompt personalizado aqui
```

Si la variable no existe, se usa el prompt por defecto del pipeline.

## Crear un pipeline personalizado

### 1. Crear el directorio

```
pipelines/
  mi_pipeline/
    __init__.py      # Vacio
    pipeline.py      # Clase que hereda de Pipeline
```

### 2. Implementar la clase

```python
"""Mi pipeline personalizado."""

from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from app.pipeline import Pipeline
from app.engine import InferenceEngine
from app.conversation import ConversationManager

logger = logging.getLogger(__name__)


class MiPipeline(Pipeline):
    name = "mi_pipeline"
    system_prompt = "Eres un asistente especializado en..."
    requires_tts = False        # True si necesitas sintesis de voz
    max_history_turns = 10

    def register_routes(
        self,
        app: FastAPI,
        engine: InferenceEngine,
        convo: ConversationManager,
        llm_lock: asyncio.Lock,
    ) -> None:

        @app.post("/mi_pipeline/ask")
        async def ask(text: str):
            messages = convo.get_messages(text)
            async with llm_lock:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, lambda: engine.generate(messages)
                )
            convo.add_exchange(text, response)
            return {"response": response}

        @app.post("/mi_pipeline/reset")
        async def reset():
            convo.clear()
            return {"status": "history_cleared", "project": "mi_pipeline"}
```

### 3. Activar

```bash
PIPELINES=robot,assistant,mi_pipeline
```

## API del Pipeline base

```python
class Pipeline:
    name: str = ""                  # Identificador unico
    system_prompt: str = ""         # Prompt por defecto para el LLM
    requires_tts: bool = False      # True si algun endpoint necesita Piper
    max_history_turns: int = 10     # Tamano de la ventana de historial

    def register_routes(self, app, engine, convo, llm_lock) -> None:
        """Registra endpoints de FastAPI en app."""
        raise NotImplementedError
```

El servidor llama `register_routes()` una vez durante el arranque, pasando:
- `app` — instancia de FastAPI
- `engine` — motor de inferencia compartido (ASR + LLM + TTS)
- `convo` — gestor de historial de conversacion para este pipeline
- `llm_lock` — asyncio.Lock que serializa el acceso al LLM
