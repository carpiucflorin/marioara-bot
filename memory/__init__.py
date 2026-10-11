from __future__ import annotations

from typing import Any, Dict, List, Optional

from .db import MemoryDB


class MemoryStore:
    def __init__(self, db_path: str = "chatbot_memory.db"):
        self.db = MemoryDB(db_path=db_path)

    def save_message(self, role: str, text: str, intent: Optional[str] = None, planner_type: Optional[str] = None, confidence_score: Optional[float] = None) -> int:
        return self.db.save_message(role=role, text=text, intent=intent, planner_type=planner_type, confidence_score=confidence_score)

    def get_recent_messages(self, limit: int = 10):
        return self.db.get_recent_messages(limit=limit)

    def save_memory(self, kind: str, text: str, importance: int = 1, confidence: float = 0.5, topic: str = "", source_message_id: Optional[int] = None) -> int:
        return self.db.save_memory(kind=kind, text=text, importance=importance, confidence=confidence, topic=topic, source_message_id=source_message_id)

    def save_episode(self, summary: str, topic: str, emotion: str, tags=None) -> int:
        return self.db.save_episode(summary, topic, emotion, tags)

    def get_recent_episodes(self, limit: int = 10):
        return self.db.get_recent_episodes(limit)

    def get_relevant_memories(self, topic: Optional[str] = None, query: str = "", limit: int = 5):
        return self.db.get_relevant_memories(topic=topic, query=query, limit=limit)

    def activate_topic(self, topic: str) -> None:
        self.db.activate_topic(topic)

    def list_memories(self, limit: int = 50):
        return self.db.list_memories(limit)

    def delete_memory(self, memory_id: int) -> bool:
        return self.db.delete_memory(memory_id)

    def correct_memory(self, memory_id: int, text: str) -> bool:
        return self.db.correct_memory(memory_id, text)

    def save_state(self, key: str, value: Any) -> None:
        self.db.save_state(key, value)

    def get_state(self, key: str, default: Any = None) -> Any:
        return self.db.get_state(key, default)

    def delete_state(self, key: str) -> None:
        self.db.delete_state(key)

    def save_snapshot(self, session_id: str, content: dict) -> None:
        self.db.save_snapshot(session_id, content)

    def load_snapshot(self, session_id: str):
        return self.db.load_snapshot(session_id)

    def log_security_event(self, event_type: str, message: str, severity: str, action_taken: str) -> None:
        self.db.log_security_event(event_type, message, severity, action_taken)

    def clear_conversation_data(self) -> None:
        self.db.clear_conversation_data()

    def export(self, export_path: str) -> str:
        return self.db.export_data(export_path)

    def set_preference(self, key: str, value: Any) -> None:
        self.db.set_preference(key, str(value))

    def get_preference(self, key: str, default: Any = None) -> Any:
        value = self.db.get_preference(key, default)
        return value if value is not None else default

    def close(self):
        return True
