#!/usr/bin/env bash
set -euo pipefail

# Descarga los modelos de ML necesarios para el voice assistant.
# Idempotente: no re-descarga si ya existen.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

VENV_PATH="$PROJECT_DIR/venv"

echo ">>> Paso 1: Descargar modelo LLM (Qwen 3 1.7B Q4_K_M)"
mkdir -p models/

LLM_FILE="models/Qwen_Qwen3-1.7B-Q4_K_M.gguf"
if [ ! -f "$LLM_FILE" ]; then
    if [ ! -d "$VENV_PATH" ]; then
        echo "ERROR: No se encontro el entorno virtual en $VENV_PATH"
        echo "Crea el venv primero: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi

    # Activar venv
    source "$VENV_PATH/bin/activate"

    # Instalar huggingface-hub si no esta disponible
    if ! python3 -c "import huggingface_hub" 2>/dev/null; then
        echo "    Instalando huggingface-hub..."
        pip install huggingface-hub
    fi

    echo "    Descargando modelo LLM (~1.3 GB)..."
    "$VENV_PATH/bin/huggingface-cli" download bartowski/Qwen_Qwen3-1.7B-GGUF \
        --include "Qwen_Qwen3-1.7B-Q4_K_M.gguf" \
        --local-dir ./models

    if [ -f "$LLM_FILE" ]; then
        SIZE=$(du -h "$LLM_FILE" | cut -f1)
        echo "    Modelo LLM descargado: $LLM_FILE ($SIZE)"
    else
        echo "ERROR: La descarga del modelo LLM fallo"
        exit 1
    fi
else
    SIZE=$(du -h "$LLM_FILE" | cut -f1)
    echo "    Modelo LLM ya descargado ($SIZE), saltando"
fi

echo ">>> Paso 2: Descargar voz Piper (es_ES-davefx-medium)"
mkdir -p voices/

VOICE_ONNX="voices/es_ES-davefx-medium.onnx"
VOICE_JSON="voices/es_ES-davefx-medium.onnx.json"

if [ ! -f "$VOICE_ONNX" ]; then
    echo "    Descargando modelo de voz (~60 MB)..."
    wget -q --show-progress -O "$VOICE_ONNX" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx?download=true"
    echo "    Modelo de voz .onnx descargado"
else
    echo "    Voz Piper .onnx ya descargada, saltando"
fi

if [ ! -f "$VOICE_JSON" ]; then
    echo "    Descargando configuracion de voz..."
    wget -q --show-progress -O "$VOICE_JSON" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json?download=true"
    echo "    Configuracion de voz .onnx.json descargada"
else
    echo "    Voz Piper .onnx.json ya descargada, saltando"
fi

echo ">>> Paso 3: Verificacion final"
echo "    Modelos:"
ls -lh models/ 2>/dev/null | grep -v "^total" | sed 's/^/        /'
echo "    Voces:"
ls -lh voices/ 2>/dev/null | grep -v "^total" | sed 's/^/        /'

# Verificar que ambos archivos existen
MISSING=0
for f in "$LLM_FILE" "$VOICE_ONNX" "$VOICE_JSON"; do
    if [ ! -f "$f" ]; then
        echo "ERROR: Falta $f"
        MISSING=1
    fi
done

if [ "$MISSING" -eq 0 ]; then
    echo ""
    echo "Todos los modelos descargados correctamente."
else
    echo ""
    echo "ERROR: Faltan archivos. Revisa los errores anteriores."
    exit 1
fi
