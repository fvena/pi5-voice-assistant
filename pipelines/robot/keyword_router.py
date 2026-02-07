"""Keyword-first intent router for robot commands.

Resolves common commands by string matching in ~1ms.
Only falls through to the LLM for unrecognized inputs.
This saves 5-7 seconds per command for the ~80% of
interactions that are simple movement/action commands.

Output format matches the LLM's structured output so
the ESP32 always receives the same JSON structure:
  {"actions": [{"action": "...", "params": {...}}]}
"""

import json
import re
from dataclasses import dataclass, field

# ── Number extraction ──────────────────────────────────────
# Matches "dos", "3", "medio", "cuarenta y cinco", etc.

WORD_NUMBERS = {
    "cero": 0, "medio": 0.5, "media": 0.5,
    "un": 1, "uno": 1, "una": 1,
    "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "quince": 15, "veinte": 20, "veinticinco": 25,
    "treinta": 30, "cuarenta": 40, "cuarenta y cinco": 45,
    "cincuenta": 50, "sesenta": 60, "noventa": 90,
    "cien": 100, "ciento": 100,
    "ciento ochenta": 180, "ciento veinte": 120,
    "trescientos sesenta": 360, "trescientos": 300,
}

# Pattern for digit numbers (e.g., "3", "45", "0.5")
DIGIT_NUMBER = re.compile(r"\b(\d+(?:[.,]\d+)?)\b")

# Pattern for special angle phrases
FULL_TURN = re.compile(r"\b(vuelta completa|giro completo|360)\b", re.I)
HALF_TURN = re.compile(r"\b(media vuelta)\b", re.I)
QUARTER_TURN = re.compile(r"\b(cuarto de vuelta)\b", re.I)

# Pattern for "N metros" / "N grados"
METERS_PATTERN = re.compile(
    r"(\w[\w\s]*?)\s*metros?", re.I
)
DEGREES_PATTERN = re.compile(
    r"(\w[\w\s]*?)\s*grados?", re.I
)


def _extract_number(text: str, pattern: re.Pattern) -> float | None:
    """Extract a number from text using a unit-specific pattern."""
    match = pattern.search(text)
    if not match:
        return None
    number_str = match.group(1).strip().lower()
    # Try word numbers first (including multi-word like "cuarenta y cinco")
    if number_str in WORD_NUMBERS:
        return WORD_NUMBERS[number_str]
    # Try digit match within the captured group
    digit_match = DIGIT_NUMBER.search(number_str)
    if digit_match:
        return float(digit_match.group(1).replace(",", "."))
    return None


# ── Command patterns ───────────────────────────────────────
# Each entry: (regex_pattern, action_type, default_params, confirmation)
# Order matters — first match wins. More specific patterns go first.

COMMAND_PATTERNS: list[tuple[re.Pattern, str, dict, str]] = [
    # ── Stop (highest priority — safety first) ──
    (re.compile(r"\b(para|stop|detente|quieto|frena|basta|alto|no te muevas)\b", re.I),
     "stop", {}, "Detenido"),

    # ── Sleep / Wake ──
    (re.compile(r"\b(duerme|duérmete|a dormir|descansa|reposo|modo reposo|relájate)\b", re.I),
     "sleep", {}, "Entrando en reposo"),
    (re.compile(r"\b(despierta|arriba|actívate|espabila|levanta|vamos)\b", re.I),
     "wake", {}, "Despertando"),

    # ── Dance ──
    (re.compile(r"\b(baila|bailar|menéate|mueve el esqueleto)\b", re.I),
     "dance", {}, "¡A bailar!"),

    # ── Movement ──
    (re.compile(r"\b(avanza|adelante|hacia adelante|camina|muévete|ve|anda|sigue|pa'?lante)\b", re.I),
     "move", {"direction": "forward", "distance": 1}, "Avanzando"),
    (re.compile(r"\b(retrocede|atrás|hacia atrás|marcha atrás|pa'?trás|recular)\b", re.I),
     "move", {"direction": "backward", "distance": 1}, "Retrocediendo"),

    # ── Turn ──
    (re.compile(r"\b(gira|tuerce|rota|dobla|voltea|da la vuelta|date la vuelta).*izquierda\b", re.I),
     "turn", {"direction": "left", "angle": 90}, "Girando a la izquierda"),
    (re.compile(r"\bizquierda\b", re.I),
     "turn", {"direction": "left", "angle": 90}, "Girando a la izquierda"),
    (re.compile(r"\b(gira|tuerce|rota|dobla|voltea|da la vuelta|date la vuelta).*derecha\b", re.I),
     "turn", {"direction": "right", "angle": 90}, "Girando a la derecha"),
    (re.compile(r"\bderecha\b", re.I),
     "turn", {"direction": "right", "angle": 90}, "Girando a la derecha"),
    # Generic turn (no direction specified) — default right
    (re.compile(r"\b(gira|tuerce|rota|dobla|voltea|da la vuelta|date la vuelta)\b", re.I),
     "turn", {"direction": "right", "angle": 90}, "Girando"),

    # ── Grab / Release ──
    (re.compile(r"\b(agarra|coge|sujeta|toma)\b", re.I),
     "grab", {}, "Agarrando"),
    (re.compile(r"\b(suelta|libera|deja|soltar)\b", re.I),
     "release", {}, "Soltando"),

    # ── Look ──
    (re.compile(r"\b(mira.*arriba|levanta.*cabeza)\b", re.I),
     "look_up", {"angle": 30}, "Mirando arriba"),
    (re.compile(r"\b(mira.*abajo|baja.*cabeza)\b", re.I),
     "look_down", {"angle": 30}, "Mirando abajo"),
]

# ── Compound command splitter ──────────────────────────────
# Splits "avanza dos metros y gira a la derecha" into two parts
COMPOUND_SPLITTER = re.compile(
    r"\s+(?:y\s+(?:luego\s+|después\s+)?|,\s*(?:luego\s+|después\s+)?|luego\s+|después\s+)",
    re.I,
)


@dataclass
class ActionResult:
    """A single action in the actions array."""
    action: str
    params: dict = field(default_factory=dict)
    confirmation: str = ""

    def to_dict(self) -> dict:
        return {"action": self.action, "params": self.params}


@dataclass
class RouterResult:
    """Result of keyword routing — may contain multiple actions."""
    matched: bool
    actions: list[ActionResult]

    def to_actions_json(self) -> dict:
        """Return the standard actions format for the ESP32."""
        return {"actions": [a.to_dict() for a in self.actions]}

    @property
    def confirmation(self) -> str:
        """Combined confirmation string for all actions."""
        return ". ".join(a.confirmation for a in self.actions if a.confirmation)


def _match_single(text: str) -> ActionResult | None:
    """Try to match a single command fragment against known patterns."""
    text_clean = text.strip().lower()
    if not text_clean:
        return None

    for pattern, action, default_params, confirmation in COMMAND_PATTERNS:
        if pattern.search(text_clean):
            params = dict(default_params)

            # Extract distance for move commands
            if action == "move":
                distance = _extract_number(text_clean, METERS_PATTERN)
                if distance is not None:
                    params["distance"] = distance

            # Extract angle for turn commands
            if action == "turn":
                if FULL_TURN.search(text_clean):
                    params["angle"] = 360
                elif HALF_TURN.search(text_clean):
                    params["angle"] = 180
                elif QUARTER_TURN.search(text_clean):
                    params["angle"] = 90
                else:
                    angle = _extract_number(text_clean, DEGREES_PATTERN)
                    if angle is not None:
                        params["angle"] = angle

            # Extract angle for look commands
            if action in ("look_up", "look_down"):
                angle = _extract_number(text_clean, DEGREES_PATTERN)
                if angle is not None:
                    params["angle"] = angle

            return ActionResult(action=action, params=params, confirmation=confirmation)

    return None


def route_command(text: str) -> RouterResult | None:
    """Try to match a command (simple or compound) by keywords.

    Returns None if no match found (meaning the LLM should handle it).
    Supports compound commands separated by "y", "y luego", commas, etc.
    """
    # Strip noise: vocatives and courtesy
    text_clean = re.sub(
        r"\b(oye|eh|hey|robot|por favor|porfa|venga|¿puedes\??|puedes)\b",
        "", text, flags=re.I
    ).strip()

    if not text_clean:
        return None

    # Try compound splitting first
    parts = COMPOUND_SPLITTER.split(text_clean)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) > 1:
        # Compound command: try to match each part
        actions = []
        for part in parts:
            result = _match_single(part)
            if result is None:
                # If any part fails to match, let the LLM handle the whole thing
                return None
            actions.append(result)
        return RouterResult(matched=True, actions=actions)

    # Single command
    result = _match_single(text_clean)
    if result is not None:
        return RouterResult(matched=True, actions=[result])

    return None  # No match → send to LLM
