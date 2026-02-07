#!/usr/bin/env bash
set -euo pipefail

# Smoke tests para los endpoints del servidor de voz.
# Asume que el servidor esta corriendo en localhost:8080.
# Requiere piper-tts instalado para generar audio de prueba.

BASE_URL="http://localhost:8080"
PASS=0
FAIL=0
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Buscar el modelo de voz
VOICE_MODEL="$PROJECT_DIR/voices/es_ES-davefx-medium.onnx"
if [ ! -f "$VOICE_MODEL" ]; then
    echo "ERROR: No se encontro el modelo de voz en $VOICE_MODEL"
    echo "Ejecuta primero: bash scripts/download-models.sh"
    exit 1
fi

check_result() {
    local test_name="$1"
    local expected="$2"
    local response="$3"

    if echo "$response" | grep -q "$expected"; then
        echo "  PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $test_name"
        echo "        Esperado: $expected"
        echo "        Recibido: $response"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Smoke tests del servidor de voz ==="
echo ""

# Test 1: Health check
echo ">>> Test 1: GET /health"
RESPONSE=$(curl -sf "$BASE_URL/health" 2>/dev/null || echo "CONNECTION_ERROR")
check_result "Health check devuelve status ok" '"status":"ok"' "$RESPONSE"

# Test 2: Robot command (keyword routing)
echo ">>> Test 2: POST /robot/command (keyword)"
TMP_WAV="/tmp/test-robot-smoke.wav"
echo "avanza" | python3 -m piper --model "$VOICE_MODEL" --output_file "$TMP_WAV" 2>/dev/null
RESPONSE=$(curl -sf -X POST "$BASE_URL/robot/command" -F "audio=@$TMP_WAV" 2>/dev/null || echo "CONNECTION_ERROR")
check_result "Robot command devuelve actions array" '"actions"' "$RESPONSE"
check_result "Robot command primera accion es move" '"action":"move"' "$RESPONSE"
rm -f "$TMP_WAV"

# Test 3: Assistant chat text (debug endpoint)
echo ">>> Test 3: POST /assistant/chat/text"
TMP_WAV="/tmp/test-assistant-smoke.wav"
echo "hola" | python3 -m piper --model "$VOICE_MODEL" --output_file "$TMP_WAV" 2>/dev/null
RESPONSE=$(curl -sf -X POST "$BASE_URL/assistant/chat/text" -F "audio=@$TMP_WAV" 2>/dev/null || echo "CONNECTION_ERROR")
check_result "Assistant text devuelve campo response" '"response"' "$RESPONSE"
rm -f "$TMP_WAV"

# Test 4: Robot reset
echo ">>> Test 4: POST /robot/reset"
RESPONSE=$(curl -sf -X POST "$BASE_URL/robot/reset" 2>/dev/null || echo "CONNECTION_ERROR")
check_result "Robot reset confirma limpieza" '"history_cleared"' "$RESPONSE"

# Test 5: Assistant reset
echo ">>> Test 5: POST /assistant/reset"
RESPONSE=$(curl -sf -X POST "$BASE_URL/assistant/reset" 2>/dev/null || echo "CONNECTION_ERROR")
check_result "Assistant reset confirma limpieza" '"history_cleared"' "$RESPONSE"

# Resumen
echo ""
echo "=== Resultados ==="
echo "    PASS: $PASS"
echo "    FAIL: $FAIL"
echo "    Total: $((PASS + FAIL))"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
