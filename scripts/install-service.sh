#!/usr/bin/env bash
set -euo pipefail

# Instala el servidor de voz como servicio systemd.
# Detecta automaticamente usuario y rutas.
# Pide confirmacion si el servicio ya existe.

echo ">>> Paso 1: Detectar contexto"
CURRENT_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PATH="$PROJECT_DIR/venv"

echo "    Usuario: $CURRENT_USER"
echo "    Proyecto: $PROJECT_DIR"
echo "    Venv: $VENV_PATH"

if [ ! -d "$VENV_PATH" ]; then
    echo "ERROR: No se encontro el entorno virtual en $VENV_PATH"
    echo "Crealo primero: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/app/main.py" ]; then
    echo "ERROR: No se encontro app/main.py en $PROJECT_DIR"
    echo "Asegurate de que el codigo de la aplicacion existe."
    exit 1
fi

SERVICE_FILE="/etc/systemd/system/voice-assistant.service"

if [ -f "$SERVICE_FILE" ]; then
    echo "    AVISO: El servicio voice-assistant ya existe."
    read -r -p "    Deseas sobreescribirlo? [s/N] " response
    case "$response" in
        [sS])
            echo "    Sobreescribiendo servicio..."
            sudo systemctl stop voice-assistant.service 2>/dev/null || true
            ;;
        *)
            echo "    Cancelado."
            exit 0
            ;;
    esac
fi

echo ">>> Paso 2: Generar unit file de systemd"
sudo tee "$SERVICE_FILE" > /dev/null << UNIT
[Unit]
Description=Unified Voice Assistant Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_PATH/bin:/usr/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="OMP_NUM_THREADS=3"
Environment="OPENBLAS_NUM_THREADS=3"
Environment="GOMP_CPU_AFFINITY=0-2"
ExecStart=$VENV_PATH/bin/uvicorn app.main:app \\
    --host 0.0.0.0 --port 8080 --workers 1 --log-level info
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=5

# Prioridad de proceso
Nice=-5
CPUAffinity=0 1 2 3

# Limites de memoria
MemoryMax=6G
MemoryHigh=5G

# Logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voice-assistant

# Seguridad
PrivateTmp=true
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
UNIT

echo "    Unit file escrito en $SERVICE_FILE"

echo ">>> Paso 3: Activar servicio"
sudo systemctl daemon-reload
sudo systemctl enable voice-assistant.service
sudo systemctl start voice-assistant.service

echo "    Esperando 5 segundos para que arranque..."
sleep 5

echo ">>> Paso 4: Verificacion"
echo "    Estado del servicio:"
sudo systemctl status voice-assistant.service --no-pager || true

echo ""
echo "    Probando health check..."
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    echo "    Health check OK"
    curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || curl -s http://localhost:8080/health
else
    echo "    AVISO: Health check fallo. Revisa los logs con: journalctl -u voice-assistant -f"
fi

echo ""
echo "Comandos utiles:"
echo "    Ver logs:      journalctl -u voice-assistant -f"
echo "    Reiniciar:     sudo systemctl restart voice-assistant"
echo "    Detener:       sudo systemctl stop voice-assistant"
echo "    Estado:        sudo systemctl status voice-assistant"
