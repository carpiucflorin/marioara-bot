from __future__ import annotations

from typing import Optional, Dict, Any


class CoherenceBuffer:
    """Tracks recent context and current conversation topic."""

    def __init__(self):
        self.messages = []
        self.current_topic = "general"

    def add_message(self, role: str, text: str):
        self.messages.append({"role": role, "text": text})
        self.messages = self.messages[-30:]
        self.current_topic = self._infer_topic(text)

    def get_recent_messages(self, limit: int = 10):
        return self.messages[-limit:]

    def get_current_topic(self) -> str:
        return self.current_topic

    def serialize(self) -> Dict[str, Any]:
        return {"messages": self.messages, "current_topic": self.current_topic}

    def restore(self, state: Dict[str, Any]):
        self.messages = state.get("messages", [])
        self.current_topic = state.get("current_topic", "general")

    def clear(self):
        self.messages.clear()
        self.current_topic = "general"

    @staticmethod
    def _infer_topic(text: str) -> str:
        lowered = (text or "").lower()
        if any(word in lowered for word in ["muzica", "music", "melodie", "artist", "album"]):
            return "music"
        if any(word in lowered for word in ["film", "movie", "serial", "cinema", "actor"]):
            return "movies"
        if any(word in lowered for word in ["job", "muncă", "șef", "team", "lucrare", "work"]):
            return "work"
        if any(word in lowered for word in ["dragă", "iubesc", "iubire", "sentiment", "love"]):
            return "love"
        return "general"
