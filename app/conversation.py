"""Per-project conversation history with sliding window and disk persistence.

History survives server restarts by saving to JSON on the NVMe.
"""

import json
import threading
import logging
from collections import deque
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversation history for a single project (robot or assistant).

    Uses a deque with fixed max length to implement a sliding window that
    automatically discards the oldest messages when the limit is reached.
    Thread-safe for concurrent access.
    Persists history to a JSON file on disk after each exchange.
    """

    def __init__(self, name: str, system_prompt: str, max_turns: int = 10,
                 persist_path: str | None = None):
        self.name = name
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.history: deque = deque(maxlen=max_turns * 2)
        self._lock = threading.Lock()
        self._persist_path = persist_path

        # Load history from disk if available
        if persist_path:
            self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load history from JSON file if it exists."""
        try:
            path = Path(self._persist_path)
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                items = data.get(self.name, [])
                for item in items:
                    self.history.append(item)
                logger.info("[%s] Loaded %d messages from disk", self.name, len(items))
        except Exception as e:
            logger.warning("[%s] Failed to load history: %s", self.name, e)

    def _save_to_disk(self) -> None:
        """Persist current history to JSON file."""
        if not self._persist_path:
            return
        try:
            path = Path(self._persist_path)
            # Read existing data to preserve other project's history
            existing = {}
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
            existing[self.name] = list(self.history)
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        except Exception as e:
            logger.warning("[%s] Failed to save history: %s", self.name, e)

    def add_exchange(self, user_text: str, assistant_text: str) -> None:
        """Record a complete user/assistant exchange and persist."""
        with self._lock:
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": assistant_text})
            self._save_to_disk()

    def get_messages(self, user_text: str) -> list[dict]:
        """Build the full message list for the LLM."""
        with self._lock:
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(list(self.history))
            messages.append({"role": "user", "content": user_text})
            return messages

    def clear(self) -> None:
        """Clear all conversation history (memory and disk)."""
        with self._lock:
            self.history.clear()
            self._save_to_disk()
