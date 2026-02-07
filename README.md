# Pi 5 Voice Assistant

Servidor de voz local para Raspberry Pi 5 que expone endpoints HTTP para un robot controlado por voz (audio → JSON) y un asistente personal (audio → audio). 100% offline, sin cloud.

---

## Arquitectura

```
ESP32 (Robot)                    ESP32 (Asistente)
     │                                │
     │  POST /robot/command           │  POST /assistant/chat
     │  audio WAV ──────┐    ┌────── audio WAV
     │                  │    │
     ▼                  ▼    ▼
   ┌──────────────────────────────────────┐
   │         Raspberry Pi 5 (8 GB)        │
   │         NVMe 256 GB                  │
   │                                      │
   │  ┌────────────────────────────────┐  │
   │  │  FastAPI Server (puerto 8080)  │  │
   │  │                                │  │
   │  │  ┌─ /robot/command ──────────┐ │  │
   │  │  │  ASR → LLM (json) ───────┼─┼──┼──→ JSON
   │  │  └───────────────────────────┘ │  │
   │  │                                │  │
   │  │  ┌─ /assistant/chat ─────────┐ │  │
   │  │  │  ASR → LLM → TTS ────────┼─┼──┼──→ WAV
   │  │  └───────────────────────────┘ │  │
   │  │                                │  │
   │  │  Modelos en memoria:           │  │
   │  │  • Whisper base (int8) ~200 MB │  │
   │  │  • Qwen 3 1.7B Q4_K_M ~2.5 GB │  │
   │  │  • Piper TTS medium    ~60 MB  │  │
   │  │  Total: ~3 GB de ~8 GB         │  │
   │  └────────────────────────────────┘  │
   └──────────────────────────────────────┘
```

---

## Requisitos

- Raspberry Pi 5 con **8 GB de RAM**
- **NVMe de 256 GB** como almacenamiento principal
- Raspberry Pi OS Lite 64-bit (Bookworm)
- Refrigeracion activa (ventilador oficial de Raspberry Pi o similar)
- Acceso SSH configurado
- Red local estable (el ESP32 se conectara por WiFi)

---

## Instalacion rapida

```bash
# Clonar el repositorio
git clone <url-del-repo> ~/voice-assistant
cd ~/voice-assistant

# Crear entorno virtual
sudo apt install -y python3-venv python3-pip
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias de compilacion (necesario para llama-cpp-python)
sudo apt install -y build-essential cmake git libopenblas-dev libcurl4-openssl-dev espeak-ng

# Compilar llama-cpp-python con optimizaciones ARM
CMAKE_ARGS="-DGGML_NATIVE=ON \
    -DGGML_BLAS=ON \
    -DGGML_BLAS_VENDOR=OpenBLAS \
    -DCMAKE_C_FLAGS='-mcpu=cortex-a76' \
    -DCMAKE_CXX_FLAGS='-mcpu=cortex-a76'" \
    pip install llama-cpp-python --no-cache-dir

# Instalar el resto de dependencias
pip install -r requirements.txt

# Copiar y editar la configuracion
cp .env.example .env
# Editar .env: configurar PIPELINES=robot,assistant (u otros)

# Ejecutar setup completo (optimizar SO + descargar modelos + instalar servicio)
make setup
```

---

## Uso

### Desarrollo (foreground)

```bash
source venv/bin/activate
make run
```

### Produccion (servicio systemd)

```bash
make service
# El servidor arranca automaticamente con el sistema
```

### Tests

```bash
make test
```

---

## Pipelines

Los endpoints del servidor son modulares y se activan via la variable `PIPELINES` en `.env`:

```bash
# Ambos pipelines (robot + asistente)
PIPELINES=robot,assistant

# Solo robot — no carga Piper TTS, ahorra ~60 MB de RAM
PIPELINES=robot

# Solo asistente
PIPELINES=assistant

# Ninguno — servidor solo con /health
PIPELINES=
```

Cada pipeline trae un system prompt por defecto. Para sobreescribirlo:

```bash
ROBOT_SYSTEM_PROMPT=Tu prompt personalizado
ASSISTANT_SYSTEM_PROMPT=Tu prompt personalizado
```

Puedes crear pipelines personalizados — ver `pipelines/README.md` para detalles.

---

## Endpoints

Los endpoints disponibles dependen de los pipelines activos. `/health` siempre esta disponible.

| Endpoint | Metodo | Entrada | Salida | Pipeline | Routing |
|---|---|---|---|---|---|
| `/health` | GET | — | JSON status | siempre | — |
| `/robot/command` | POST | audio WAV | JSON con actions array | robot | keyword → LLM |
| `/robot/reset` | POST | — | JSON confirmacion | robot | — |
| `/assistant/chat` | POST | audio WAV | audio WAV | assistant | streaming LLM→TTS |
| `/assistant/chat/stream` | POST | audio WAV | chunks binarios | assistant | streaming chunked |
| `/assistant/chat/text` | POST | audio WAV | JSON texto | assistant | streaming LLM |
| `/assistant/reset` | POST | — | JSON confirmacion | assistant | — |

### Formato de respuesta del robot

Tanto el keyword router como el LLM devuelven el mismo formato:

```json
{"actions": [{"action": "tipo", "params": {...}}]}
```

El ESP32 siempre itera `doc["actions"]` — no hay dos formatos distintos.

**Acciones disponibles:**

| Accion | Parametros | Defaults |
|--------|-----------|----------|
| `move` | direction (forward/backward), distance (metros) | distance=1, direction=forward |
| `turn` | direction (left/right), angle (grados) | angle=90, direction=right |
| `stop` | {} | — |
| `sleep` | {} | — |
| `wake` | {} | — |
| `dance` | {} | — |
| `grab` | {} | — |
| `release` | {} | — |
| `look_up` | angle (grados) | angle=30 |
| `look_down` | angle (grados) | angle=30 |
| `unknown` | original (texto del usuario) | — |

---

## Configuracion

Copia `.env.example` a `.env` y ajusta los valores segun tu entorno:

| Variable | Descripcion | Valor por defecto |
|---|---|---|
| `MODEL_PATH` | Ruta al modelo LLM GGUF | `./models/Qwen_Qwen3-1.7B-Q4_K_M.gguf` |
| `N_THREADS` | Hilos para inferencia LLM | `3` |
| `N_CTX` | Ventana de contexto (tokens) | `2048` |
| `N_BATCH` | Tokens por batch | `256` |
| `MAX_TOKENS` | Tokens maximos de respuesta | `256` |
| `TEMPERATURE` | Temperatura de generacion | `0.7` |
| `WHISPER_MODEL` | Modelo Whisper (tiny/base/small) | `base` |
| `WHISPER_LANGUAGE` | Idioma de transcripcion | `es` |
| `PIPER_VOICE` | Ruta al modelo de voz Piper | `./voices/es_ES-davefx-medium.onnx` |
| `HOST` | Direccion de escucha | `0.0.0.0` |
| `PORT` | Puerto del servidor | `8080` |
| `MAX_HISTORY_TURNS` | Turnos maximos de historial | `10` |
| `HISTORY_FILE` | Archivo de persistencia del historial | `./conversation_history.json` |
| `PIPELINES` | Pipelines a activar (separados por comas) | *(vacio)* |
| `ROBOT_SYSTEM_PROMPT` | Override del prompt del robot | *(prompt del pipeline)* |
| `ASSISTANT_SYSTEM_PROMPT` | Override del prompt del asistente | *(prompt del pipeline)* |

---

## Estructura del proyecto

```
pi5-voice-assistant/
├── .env.example                 # Template de configuracion
├── .gitignore
├── Makefile                     # make setup / run / test / service / clean
├── README.md                    # Este archivo
├── TUTORIAL.md                  # Tutorial completo de referencia
├── requirements.txt             # Dependencias Python
├── app/
│   ├── __init__.py              # Vacio
│   ├── config.py                # Settings desde .env (incluye PIPELINES)
│   ├── pipeline.py              # Clase base Pipeline
│   ├── conversation.py          # Historial con persistencia JSON en NVMe
│   ├── engine.py                # Motor: ASR + LLM + TTS (carga condicional)
│   └── main.py                  # FastAPI app con carga dinamica de pipelines
├── pipelines/
│   ├── README.md                # Tutorial para crear pipelines personalizados
│   ├── robot/
│   │   ├── pipeline.py          # RobotPipeline (keyword router + LLM fallback)
│   │   └── keyword_router.py    # Router regex para comandos robot (~1ms)
│   └── assistant/
│       └── pipeline.py          # AssistantPipeline (streaming LLM→TTS)
├── scripts/
│   ├── system-optimize.sh       # Optimizacion SO de la Pi 5
│   ├── download-models.sh       # Descarga modelos LLM y TTS
│   └── install-service.sh       # Instala systemd unit
└── tests/
    ├── test_keyword_router.py   # Tests unitarios pytest (60+ casos)
    └── test_endpoints.sh        # Smoke tests con curl
```

---

## Rendimiento esperado

| Escenario | Pipeline | Latencia esperada |
|---|---|---|
| Robot: comando simple (keyword) | ASR → keyword match | **2-4s** |
| Robot: comando complejo (LLM) | ASR → LLM (JSON) | **8-12s** |
| Asistente (streaming) | ASR → LLM stream → TTS stream | **5-11s** |
| Asistente (primera frase) | ASR → primera frase LLM → TTS | **5-8s** |

---

## Licencia

MIT
