"""Tests unitarios para el keyword router de comandos del robot.

Bateria de 60+ tests organizados por categoria. Verifican el formato
actions array: result.actions[i].action y result.actions[i].params.
"""

import pytest

from pipelines.robot.keyword_router import route_command


class TestStop:
    """Comandos de parada — maxima prioridad (seguridad)."""

    def test_para(self):
        result = route_command("para")
        assert result is not None
        assert result.actions[0].action == "stop"
        assert result.actions[0].params == {}

    def test_detente(self):
        result = route_command("detente")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_quieto(self):
        result = route_command("quieto")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_no_te_muevas(self):
        result = route_command("no te muevas")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_frena(self):
        result = route_command("frena")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_stop(self):
        result = route_command("stop")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_basta(self):
        result = route_command("basta")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_alto(self):
        result = route_command("alto")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_oye_robot_para(self):
        result = route_command("oye robot para")
        assert result is not None
        assert result.actions[0].action == "stop"

    def test_por_favor_detente(self):
        result = route_command("por favor detente")
        assert result is not None
        assert result.actions[0].action == "stop"


class TestMoveForward:
    """Comandos de avance — con extraccion de distancia."""

    def test_avanza(self):
        result = route_command("avanza")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 1

    def test_avanza_dos_metros(self):
        result = route_command("avanza dos metros")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 2

    def test_avanza_3_metros(self):
        result = route_command("avanza 3 metros")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 3

    def test_ve_hacia_adelante(self):
        result = route_command("ve hacia adelante")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"

    def test_camina(self):
        result = route_command("camina")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"

    def test_muevete(self):
        result = route_command("muévete")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"

    def test_anda(self):
        result = route_command("anda")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"

    def test_adelante(self):
        result = route_command("adelante")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"

    def test_avanza_medio_metro(self):
        result = route_command("avanza medio metro")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 0.5


class TestMoveBackward:
    """Comandos de retroceso — con extraccion de distancia."""

    def test_retrocede(self):
        result = route_command("retrocede")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"
        assert result.actions[0].params["distance"] == 1

    def test_retrocede_dos_metros(self):
        result = route_command("retrocede dos metros")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"
        assert result.actions[0].params["distance"] == 2

    def test_ve_hacia_atras(self):
        result = route_command("ve hacia atrás")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"

    def test_marcha_atras(self):
        result = route_command("marcha atrás")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"

    def test_atras(self):
        result = route_command("atrás")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"

    def test_retrocede_medio_metro(self):
        result = route_command("retrocede medio metro")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"
        assert result.actions[0].params["distance"] == 0.5


class TestTurn:
    """Comandos de giro — con extraccion de angulo."""

    def test_gira_derecha(self):
        result = route_command("gira a la derecha")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "right"
        assert result.actions[0].params["angle"] == 90

    def test_gira_izquierda(self):
        result = route_command("gira a la izquierda")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "left"
        assert result.actions[0].params["angle"] == 90

    def test_gira_45_grados_derecha(self):
        result = route_command("gira 45 grados a la derecha")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "right"
        assert result.actions[0].params["angle"] == 45

    def test_gira_180_grados(self):
        result = route_command("gira 180 grados")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["angle"] == 180

    def test_da_la_vuelta(self):
        result = route_command("da la vuelta")
        assert result is not None
        assert result.actions[0].action == "turn"

    def test_vuelta_completa(self):
        result = route_command("da una vuelta completa")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["angle"] == 360

    def test_media_vuelta(self):
        result = route_command("da media vuelta")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["angle"] == 180

    def test_tuerce_izquierda(self):
        result = route_command("tuerce a la izquierda")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "left"

    def test_rota_derecha(self):
        result = route_command("rota a la derecha")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "right"


class TestSleepWake:
    """Comandos de reposo y despertar."""

    def test_duermete(self):
        result = route_command("duérmete")
        assert result is not None
        assert result.actions[0].action == "sleep"
        assert result.actions[0].params == {}

    def test_a_dormir(self):
        result = route_command("a dormir")
        assert result is not None
        assert result.actions[0].action == "sleep"

    def test_descansa(self):
        result = route_command("descansa")
        assert result is not None
        assert result.actions[0].action == "sleep"

    def test_modo_reposo(self):
        result = route_command("modo reposo")
        assert result is not None
        assert result.actions[0].action == "sleep"

    def test_despierta(self):
        result = route_command("despierta")
        assert result is not None
        assert result.actions[0].action == "wake"
        assert result.actions[0].params == {}

    def test_arriba(self):
        result = route_command("arriba")
        assert result is not None
        assert result.actions[0].action == "wake"

    def test_activate(self):
        result = route_command("actívate")
        assert result is not None
        assert result.actions[0].action == "wake"


class TestDance:
    """Comandos de baile."""

    def test_baila(self):
        result = route_command("baila")
        assert result is not None
        assert result.actions[0].action == "dance"
        assert result.actions[0].params == {}

    def test_ponte_a_bailar(self):
        result = route_command("ponte a bailar")
        assert result is not None
        assert result.actions[0].action == "dance"


class TestCompound:
    """Comandos compuestos — generan multiples acciones."""

    def test_avanza_y_gira(self):
        result = route_command("avanza dos metros y gira a la derecha")
        assert result is not None
        assert len(result.actions) == 2
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 2
        assert result.actions[1].action == "turn"
        assert result.actions[1].params["direction"] == "right"
        assert result.actions[1].params["angle"] == 90

    def test_avanza_y_luego_gira(self):
        result = route_command("avanza un metro y luego gira a la izquierda")
        assert result is not None
        assert len(result.actions) == 2
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 1
        assert result.actions[1].action == "turn"
        assert result.actions[1].params["direction"] == "left"

    def test_retrocede_y_baila(self):
        result = route_command("retrocede medio metro y baila")
        assert result is not None
        assert len(result.actions) == 2
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "backward"
        assert result.actions[0].params["distance"] == 0.5
        assert result.actions[1].action == "dance"

    def test_gira_y_avanza(self):
        result = route_command("gira a la derecha y avanza tres metros")
        assert result is not None
        assert len(result.actions) == 2
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "right"
        assert result.actions[1].action == "move"
        assert result.actions[1].params["direction"] == "forward"
        assert result.actions[1].params["distance"] == 3

    def test_triple_compound(self):
        result = route_command("avanza, gira a la derecha y avanza otra vez")
        assert result is not None
        assert len(result.actions) == 3
        assert result.actions[0].action == "move"
        assert result.actions[1].action == "turn"
        assert result.actions[2].action == "move"


class TestNoise:
    """Vocativos y cortesia — se filtran antes de matchear."""

    def test_oye_robot_avanza(self):
        result = route_command("oye robot avanza")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"

    def test_por_favor_gira(self):
        result = route_command("por favor gira a la derecha")
        assert result is not None
        assert result.actions[0].action == "turn"
        assert result.actions[0].params["direction"] == "right"

    def test_oye_robot_por_favor_avanza(self):
        result = route_command("oye robot por favor avanza dos metros")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"
        assert result.actions[0].params["distance"] == 2

    def test_venga_anda(self):
        result = route_command("venga anda para delante")
        assert result is not None
        assert result.actions[0].action == "move"
        assert result.actions[0].params["direction"] == "forward"


class TestNoMatch:
    """Textos no reconocidos — devuelven None (fallback al LLM)."""

    def test_canta_cancion(self):
        result = route_command("canta una canción")
        assert result is None

    def test_capital_francia(self):
        result = route_command("cuál es la capital de Francia")
        assert result is None

    def test_llama_madre(self):
        result = route_command("llama a mi madre")
        assert result is None

    def test_que_hora_es(self):
        result = route_command("qué hora es")
        assert result is None
