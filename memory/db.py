import sqlite3
import json
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


class MemoryDB:
    def __init__(self, db_path: str = "chatbot_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    role TEXT NOT NULL,
                    text TEXT NOT NULL,
                    intent TEXT,
                    planner_type TEXT,
                    confidence_score REAL,
                    feedback TEXT
                )
                """
            )
            message_columns = {row["name"] for row in conn.execute("PRAGMA table_info(messages)")}
            for column, definition in (
                ("planner_type", "TEXT"),
                ("confidence_score", "REAL"),
                ("feedback", "TEXT"),
            ):
                if column not in message_columns:
                    conn.execute(f"ALTER TABLE messages ADD COLUMN {column} {definition}")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    text TEXT NOT NULL,
                    importance INTEGER NOT NULL DEFAULT 1,
                    confidence REAL NOT NULL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT,
                    use_count INTEGER NOT NULL DEFAULT 0,
                    source_message_id INTEGER,
                    topic TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    topic TEXT NOT NULL DEFAULT '',
                    emotion TEXT NOT NULL DEFAULT 'neutral',
                    tags_json TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    due_ts TEXT NOT NULL,
                    text TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                )
                """
            )
            conn.execute("CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS snapshots (
                    session_id TEXT PRIMARY KEY,
                    content_json TEXT NOT NULL,
                    created_ts TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message_preview TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    action_taken TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_message(self, role: str, text: str, intent: Optional[str] = None, planner_type: Optional[str] = None, confidence_score: Optional[float] = None) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO messages (ts, role, text, intent, planner_type, confidence_score) VALUES (?, ?, ?, ?, ?, ?)",
                (self._now(), role, text, intent, planner_type, confidence_score),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_recent_messages(self, limit: int = 10):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, role, text, intent, planner_type, confidence_score, feedback FROM messages ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [tuple(row) for row in rows[::-1]]

    def save_memory(self, kind: str, text: str, importance: int = 1, confidence: float = 0.5, topic: str = "", source_message_id: Optional[int] = None) -> int:
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM memories WHERE kind = ? AND lower(text) = lower(?) AND topic = ? LIMIT 1",
                (kind, text, topic),
            ).fetchone()
            if existing is not None:
                conn.execute(
                    "UPDATE memories SET importance = MAX(importance, ?), confidence = MAX(confidence, ?), is_active = 1 WHERE id = ?",
                    (importance, confidence, existing["id"]),
                )
                return int(existing["id"])
            cursor = conn.execute(
                """
                INSERT INTO memories (kind, text, importance, confidence, created_at, last_used_at, use_count, source_message_id, topic, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    kind,
                    text,
                    importance,
                    confidence,
                    self._now(),
                    self._now(),
                    0,
                    source_message_id,
                    topic,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def save_episode(self, summary: str, topic: str, emotion: str, tags=None) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO episodes (created_at, summary, topic, emotion, tags_json) VALUES (?, ?, ?, ?, ?)",
                (self._now(), summary, topic, emotion, json.dumps(tags or [], ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def get_recent_episodes(self, limit: int = 10):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, created_at, summary, topic, emotion, tags_json FROM episodes ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            (row["id"], row["created_at"], row["summary"], row["topic"], row["emotion"], json.loads(row["tags_json"]))
            for row in reversed(rows)
        ]

    def get_relevant_memories(self, topic: Optional[str] = None, query: str = "", limit: int = 5):
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, kind, text, importance, confidence, created_at, last_used_at,
                       use_count, source_message_id, topic, is_active
                FROM memories
                WHERE is_active = 1 AND (? IS NULL OR topic = ? OR topic = '')
                """,
                (topic, topic),
            ).fetchall()

            query_terms = self._terms(query)
            ranked = []
            now = datetime.now()
            for row in rows:
                memory_terms = self._terms(row["text"])
                overlap = len(query_terms & memory_terms) / max(1, len(query_terms)) if query_terms else 0.0
                if query_terms and overlap == 0 and row["topic"] != topic:
                    continue
                try:
                    age_days = max(0.0, (now - datetime.fromisoformat(row["created_at"])).total_seconds() / 86400)
                except (TypeError, ValueError):
                    age_days = 365.0
                recency = 0.5 ** (age_days / 14.0)
                score = 0.6 * overlap + 0.25 * (row["importance"] / 5.0) + 0.15 * recency
                ranked.append((score, row))

            ranked.sort(key=lambda item: item[0], reverse=True)
            selected = [row for _, row in ranked[:limit]]
            if selected:
                conn.executemany(
                    "UPDATE memories SET last_used_at = ?, use_count = use_count + 1 WHERE id = ?",
                    [(self._now(), row["id"]) for row in selected],
                )
            return [tuple(row) for row in selected]

    def activate_topic(self, topic: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET is_active = CASE WHEN topic = ? OR topic = '' THEN 1 ELSE 0 END",
                (topic,),
            )

    def list_memories(self, limit: int = 50):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, kind, text, importance, topic, is_active FROM memories ORDER BY importance DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [tuple(row) for row in rows]

    def delete_memory(self, memory_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def correct_memory(self, memory_id: int, text: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE memories SET text = ?, confidence = 1.0, last_used_at = ? WHERE id = ?",
                (text, self._now(), memory_id),
            )
            return cursor.rowcount > 0

    @staticmethod
    def _terms(text: str):
        stop_words = {"este", "sunt", "care", "pentru", "despre", "asta", "acest", "aceasta", "vreau", "place", "lui", "mea", "meu"}
        return {term for term in re.findall(r"[a-zăâîșț]{3,}", (text or "").lower()) if term not in stop_words}

    def save_state(self, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO app_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM app_state WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (TypeError, json.JSONDecodeError):
            return default

    def delete_state(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM app_state WHERE key = ?", (key,))

    def save_snapshot(self, session_id: str, content: Dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO snapshots (session_id, content_json, created_ts) VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET content_json = excluded.content_json, created_ts = excluded.created_ts",
                (session_id, json.dumps(content, ensure_ascii=False), self._now()),
            )
            cutoff = datetime.fromtimestamp(datetime.now().timestamp() - 86400).isoformat(timespec="seconds")
            conn.execute("DELETE FROM snapshots WHERE created_ts < ?", (cutoff,))

    def load_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT content_json, created_ts FROM snapshots WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            created = datetime.fromisoformat(row["created_ts"])
            if (datetime.now() - created).total_seconds() > 86400:
                return None
            return {"content": json.loads(row["content_json"]), "created_ts": row["created_ts"]}
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

    def log_security_event(self, event_type: str, message: str, severity: str, action_taken: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO security_events (ts, event_type, message_preview, severity, action_taken) VALUES (?, ?, ?, ?, ?)",
                (self._now(), event_type, message[:160], severity, action_taken),
            )

    def clear_conversation_data(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages")
            conn.execute("DELETE FROM memories")
            conn.execute("DELETE FROM episodes")
            conn.execute("DELETE FROM snapshots")
            conn.execute("DELETE FROM app_state WHERE key != 'legacy_json_migrated'")
            conn.execute("DELETE FROM preferences")
            conn.execute("DELETE FROM reminders")

    def export_data(self, export_path: str) -> str:
        tables = ("messages", "memories", "episodes", "preferences", "reminders", "app_state", "security_events")
        exported = {}
        with self._connect() as conn:
            for table in tables:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                exported[table] = [dict(row) for row in rows]
        target = Path(export_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(exported, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(target)

    def set_preference(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
            conn.commit()

    def get_preference(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM preferences WHERE key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return default
            return row["value"]

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")
