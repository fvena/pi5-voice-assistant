.PHONY: setup run test service clean

# Ejecuta los 3 scripts de setup en orden
setup:
	bash scripts/system-optimize.sh
	bash scripts/download-models.sh
	bash scripts/install-service.sh

# Arranca el servidor en foreground (para desarrollo)
run:
	OMP_NUM_THREADS=3 OPENBLAS_NUM_THREADS=3 \
	./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1

# Ejecuta tests unitarios + smoke tests
test:
	./venv/bin/pytest tests/test_keyword_router.py -v
	bash tests/test_endpoints.sh

# Solo instala/reinicia el servicio systemd
service:
	bash scripts/install-service.sh

# Limpia archivos generados (NO borra modelos)
clean:
	rm -f conversation_history.json
	rm -f test-*.wav
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
