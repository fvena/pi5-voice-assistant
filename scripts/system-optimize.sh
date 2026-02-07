#!/usr/bin/env bash
set -euo pipefail

# Optimizacion del sistema operativo de Raspberry Pi 5 para inferencia LLM.
# Idempotente: puede ejecutarse multiples veces sin romper nada.
# Requiere sudo.

# Comprobar que estamos en una Pi 5
if ! grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
    echo "ERROR: Este script esta disenado para Raspberry Pi 5."
    echo "Modelo detectado: $(cat /proc/device-tree/model 2>/dev/null || echo 'desconocido')"
    exit 1
fi

echo ">>> Paso 1: Fijar CPU governor en performance"
echo performance | sudo tee /sys/devices/system/cpu/cpufreq/policy0/scaling_governor > /dev/null

GOVERNOR_SERVICE="/etc/systemd/system/cpu-governor.service"
if [ ! -f "$GOVERNOR_SERVICE" ]; then
    sudo tee "$GOVERNOR_SERVICE" > /dev/null << 'UNIT'
[Unit]
Description=Set CPU governor to performance
After=multi-user.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo performance > /sys/devices/system/cpu/cpufreq/policy0/scaling_governor"

[Install]
WantedBy=multi-user.target
UNIT
    sudo systemctl daemon-reload
    sudo systemctl enable cpu-governor.service
    echo "    Servicio cpu-governor creado y habilitado"
else
    echo "    Servicio cpu-governor ya existe, saltando"
fi
sudo systemctl start cpu-governor.service || true

echo ">>> Paso 2: Configurar swap con zram + NVMe"
sudo apt install -y zram-tools

ZRAM_CONF="/etc/default/zramswap"
if ! grep -q "^ALGO=lz4" "$ZRAM_CONF" 2>/dev/null; then
    sudo tee "$ZRAM_CONF" > /dev/null << 'ZRAM'
ALGO=lz4
SIZE=2048
PRIORITY=100
ZRAM
    echo "    zramswap configurado"
else
    echo "    zramswap ya configurado, saltando"
fi

if [ ! -f /swapfile ]; then
    echo "    Creando swapfile de 2 GB en NVMe..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo "    Swapfile creado y activado"
else
    echo "    /swapfile ya existe, saltando"
fi

if ! grep -q "/swapfile" /etc/fstab 2>/dev/null; then
    echo '/swapfile none swap sw,pri=10 0 0' | sudo tee -a /etc/fstab > /dev/null
    echo "    Entrada de swapfile anadida a /etc/fstab"
else
    echo "    /swapfile ya esta en /etc/fstab, saltando"
fi

echo ">>> Paso 3: Parametros del kernel para LLM"
SYSCTL_PARAMS=(
    "vm.swappiness=100"
    "vm.vfs_cache_pressure=500"
    "vm.page-cluster=0"
    "vm.dirty_background_ratio=1"
    "vm.dirty_ratio=50"
)

for param in "${SYSCTL_PARAMS[@]}"; do
    if ! grep -q "^${param}$" /etc/sysctl.conf 2>/dev/null; then
        echo "$param" | sudo tee -a /etc/sysctl.conf > /dev/null
        echo "    Anadido: $param"
    else
        echo "    Ya existe: $param"
    fi
done
sudo sysctl -p > /dev/null 2>&1

echo ">>> Paso 4: Desactivar servicios innecesarios"
sudo systemctl disable bluetooth hciuart avahi-daemon triggerhappy 2>/dev/null || true
sudo apt purge -y modemmanager 2>/dev/null || true
sudo systemctl disable NetworkManager-wait-online.service 2>/dev/null || true
echo "    Servicios innecesarios desactivados"

echo ">>> Paso 5: Optimizacion de arranque"
CONFIG_TXT="/boot/firmware/config.txt"
if [ -f "$CONFIG_TXT" ]; then
    if ! grep -q "initial_turbo=30" "$CONFIG_TXT" 2>/dev/null; then
        echo "initial_turbo=30" | sudo tee -a "$CONFIG_TXT" > /dev/null
        echo "    initial_turbo=30 anadido a config.txt"
    else
        echo "    initial_turbo=30 ya existe en config.txt"
    fi
else
    echo "    AVISO: $CONFIG_TXT no encontrado, saltando"
fi

CMDLINE_TXT="/boot/firmware/cmdline.txt"
if [ -f "$CMDLINE_TXT" ]; then
    for opt in quiet fastboot noatime; do
        if ! grep -q "$opt" "$CMDLINE_TXT" 2>/dev/null; then
            sudo sed -i "s/$/ $opt/" "$CMDLINE_TXT"
            echo "    $opt anadido a cmdline.txt"
        else
            echo "    $opt ya existe en cmdline.txt"
        fi
    done
else
    echo "    AVISO: $CMDLINE_TXT no encontrado, saltando"
fi

echo ">>> Paso 6: Verificacion final"
echo "    Governor: $(cat /sys/devices/system/cpu/cpufreq/policy0/scaling_governor)"
echo "    Swap activo:"
swapon --show 2>/dev/null | sed 's/^/        /'
echo "    Temperatura: $(vcgencmd measure_temp 2>/dev/null || echo 'no disponible')"
echo "    Throttling: $(vcgencmd get_throttled 2>/dev/null || echo 'no disponible')"
echo ""
echo "Reinicia con 'sudo reboot' para aplicar todos los cambios."
