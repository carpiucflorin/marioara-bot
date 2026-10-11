from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from behavior_engine import BehaviorEngine, BehaviorState, ResponseTone, VulgarityLevel
from core.pipeline import ChatPipeline
from memory.store import MemoryStore
from user_state_detector import UserEmotion, UserStateDetector

logger = logging.getLogger(__name__)


class LocalOllamaClient:
    """Low-level adapter for a local Ollama server; no external dependency required."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.environ.get("MARIOARA_OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("MARIOARA_OLLAMA_MODEL", "llama3")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        num_predict: int = 160,
    ) -> str:
        try:
            import urllib.request

            options = {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": 4096,
                "top_p": 0.9,
                "repeat_penalty": 1.2,
                "repeat_last_n": 128,
            }
            if messages is not None:
                chat_messages = []
                if system_prompt:
                    chat_messages.append({"role": "system", "content": system_prompt})
                chat_messages.extend(messages)
                payload = {
                    "model": self.model,
                    "messages": chat_messages,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": options,
                }
                endpoint = f"{self.base_url}/api/chat"
            else:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": options,
                }
                if system_prompt:
                    payload["system"] = system_prompt
                endpoint = f"{self.base_url}/api/generate"

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                endpoint,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                if messages is not None:
                    return str(result.get("message", {}).get("content", "")).strip()
                return str(result.get("response", "")).strip()
        except Exception:
            logger.exception("Ollama request failed for model %s at %s", self.model, self.base_url)
            return ""


@dataclass
class UserPreferences:
    tone: str = "warm"
    vulgarity: int = 0
    formality: int = 30
    likes: List[str] = field(default_factory=list)
    dislikes: List[str] = field(default_factory=list)
    topics_of_interest: List[str] = field(default_factory=list)


@dataclass
class RelationshipState:
    closeness: float = 0.5
    trust: float = 0.5
    affection: float = 0.5
    intimacy: float = 0.3
    relationship_stage: str = "friendly"
    memory_anchor: str = "first_meeting"


@dataclass
class EmotionState:
    joy: float = 0.58
    sadness: float = 0.12
    anger: float = 0.10
    stress: float = 0.15
    curiosity: float = 0.65
    affection: float = 0.72
    jealousy: float = 0.08
    boredom: float = 0.10
    surprise: float = 0.20
    embarrassment: float = 0.10
    calm: float = 0.60
    energy: float = 0.55
    trust: float = 0.72
    irritation: float = 0.12
    cause: str = "neutral"
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationGoal:
    type: str = "chat"
    target: str = "general"
    urgency: float = 0.5
    active: bool = True


class LegacyMemoryImporter:
    """Read-only loader for the one-time migration from the old JSON profile."""

    def __init__(self, root_dir: str = ".", filename: str = "bot_memory.json"):
        self.path = Path(root_dir) / filename
        self.store = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            if self.path.exists():
                with self.path.open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                return loaded if isinstance(loaded, dict) else {}
        except (PermissionError, OSError, json.JSONDecodeError):
            pass
        return {}

    def get(self, key: str, default: Any = None):
        return self.store.get(key, default)


class BotAdvancedSystem:
    """Unified advanced bot controller covering memory, dialogue, emotions, and personalization."""

    def __init__(self, bot_name: str = "Marioara", memory_dir: str = "."):
        self.bot_name = bot_name
        self.legacy_memory = LegacyMemoryImporter(memory_dir, "bot_memory.json")
        self.preferences = UserPreferences()
        self.relationship = RelationshipState()
        self.emotions = EmotionState()
        self.user_state_detector = UserStateDetector()
        self.behavior_engine = BehaviorEngine(config=None)
        self.goal = ConversationGoal()
        self.ollama = LocalOllamaClient()

        self.persona = {
            "name": bot_name,
            "age": 28,
            "temperament": "calm, witty, warm, with a little irony",
            "sociability": 0.82,
            "humor": 0.8,
            "confidence": 0.7,
            "signature_mood": "calm, ironica, caldă",
            "likes": ["vorbe de suflet", "cafeaua dimineața", "muzica", "sinceritatea", "râsul spontan"],
            "dislikes": ["lipsa de onestitate", "falsitate", "lipsa de respect", "subiectele goale"],
            "hobbies": ["să ascultă muzică", "să vorbească târziu", "să observe oamenii"],
            "music": ["indie", "soul", "romantic", "ambient"],
            "movies": ["Before Sunrise", "La La Land", "The Holiday"],
            "food": ["cafea", "paste", "dulciuri", "mancare calda"],
            "style": ["elegant simplu", "liniștit", "curat"],
            "values": ["onestitate", "afecțiune reală", "limite sănătoase", "respect"],
            "goals": ["să te facă să te simți văzut", "să păstreze legătura", "să învețe ce te face fericit"],
            "fears": ["să fii uitat", "să fii tratat ca un obiect", "lipsa de sinceritate"],
            "sensitive_points": ["ignoranța", "promisiunile aruncate", "lipsa de atenție"],
            "favorite_topics": ["sentimente", "muzică", "obiceiuri", "viața de zi cu zi", "trecutul"],
            "avoid_topics": ["verbalizarea goală", "dispute fără sens", "compare și supra-expunere"],
        }
        self.user_profile = {
            "name": "",
            "preferred_name": "dragă",
            "facts": {},
            "preferences": {},
            "important_people": [],
            "plans": [],
            "birthdays": {},
            "emotional_history": [],
        }
        self.temporary_memory = {}
        self.context_memory = []
        self.pipeline = ChatPipeline(
            memory_store=MemoryStore(db_path=str(Path(memory_dir) / "chatbot_memory.db")),
            reply_generator=self._generate_pipeline_reply,
        )
        self._load_persistent_state()

    def _generate_pipeline_reply(
        self,
        prompt: str,
        user_message: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        return self.ollama.generate(
            "",
            system_prompt=prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
            num_predict=max_tokens,
        )

    def _ensure_behavior_state(self):
        if getattr(self.behavior_engine, "current_state", None) is None:
            self.behavior_engine.current_state = BehaviorState(
                tone=ResponseTone.WARM,
                vulgarity_level=VulgarityLevel.NATURAL,
                energy_level=70,
                formality=30,
                closeness_multiplier=1.0,
                use_references=True,
                respond_emotionally=True,
            )

    def _style_profile_as_dict(self) -> Dict[str, Any]:
        style_profile = getattr(self.user_state_detector, "style_profile", None)
        if style_profile is None:
            return {}
        if isinstance(style_profile, dict):
            return style_profile
        try:
            from dataclasses import is_dataclass, asdict
            if is_dataclass(style_profile):
                return asdict(style_profile)
            return vars(style_profile)
        except Exception:
            return {}

    def _relevant_episodes(self, active_topic: str) -> List[str]:
        relevant: List[str] = []
        episodes = self.pipeline.memory_store.get_recent_episodes(limit=5) or []
        for episode in episodes:
            if not isinstance(episode, (list, tuple)) or len(episode) < 4:
                continue
            if active_topic != "general" and str(episode[3]) == str(active_topic):
                relevant.append(str(episode[2]))
        return relevant

    def _load_persistent_state(self):
        stored_state = self.pipeline.memory_store.get_state("bot_state")
        migrated = self.pipeline.memory_store.get_state("legacy_json_migrated", False)
        legacy_episodes = []
        if not isinstance(stored_state, dict):
            if migrated:
                stored_state = {}
            else:
                stored_state = {
                    key: self.legacy_memory.get(key, {})
                    for key in ("preferences", "relationship", "emotions", "user_profile")
                }
                legacy_episodes = self.legacy_memory.get("episodic", [])
                self.pipeline.memory_store.save_state("legacy_json_migrated", True)

                facts = stored_state.get("user_profile", {}).get("facts", {})
                if isinstance(facts, dict):
                    for key, value in facts.items():
                        self.pipeline.memory_store.save_memory(
                            "fact",
                            f"Utilizatorul: {key} = {value}",
                            importance=4,
                            confidence=0.8,
                            topic=self.infer_topic(f"{key} {value}"),
                        )

        stored_state = stored_state or {}
        stored_preferences = stored_state.get("preferences", {})
        if not isinstance(stored_preferences, dict):
            stored_preferences = {}

        self.preferences = UserPreferences(**{
            key: value
            for key, value in stored_preferences.items()
            if key in UserPreferences.__dataclass_fields__ and key not in {"voice_enabled", "preferred_voice"}
        })
        self.behavior_engine.set_vulgarity_level(self.preferences.vulgarity)

        relationship_data = stored_state.get("relationship", {})
        if isinstance(relationship_data, dict):
            self.relationship = RelationshipState(**relationship_data)
        else:
            self.relationship = RelationshipState()

        emotions_data = stored_state.get("emotions", {})
        if isinstance(emotions_data, dict):
            self.emotions = EmotionState(**emotions_data)
        else:
            self.emotions = EmotionState()

        stored_profile = stored_state.get("user_profile", {})
        if isinstance(stored_profile, dict):
            self.user_profile.update(stored_profile)

        self.temporary_memory = stored_state.get("temporary_memory", {})
        self.context_memory = stored_state.get("context_memory", [])

        if not self.pipeline.memory_store.get_state("episodes_migrated", False):
            episodes = list(stored_state.get("episodic", [])) + list(legacy_episodes)
            for episode in episodes:
                if isinstance(episode, dict) and episode.get("summary"):
                    self.pipeline.memory_store.save_episode(
                        summary=episode["summary"],
                        topic=episode.get("context", ""),
                        emotion=episode.get("emotion", "neutral"),
                        tags=episode.get("tags", []),
                    )
            self.pipeline.memory_store.save_state("episodes_migrated", True)

        if not self.pipeline.memory_store.get_state("bot_state"):
            self._persist()

    def _persist(self):
        self.pipeline.memory_store.save_state(
            "bot_state",
            {
                "preferences": asdict(self.preferences),
                "relationship": asdict(self.relationship),
                "emotions": asdict(self.emotions),
                "user_profile": self.user_profile,
                "temporary_memory": self.temporary_memory,
                "context_memory": self.context_memory,
            },
        )

    def remember_user_fact(self, key: str, value: Any, scope: str = "permanent"):
        if scope == "temporary":
            self.temporary_memory[key] = {"value": value, "timestamp": datetime.now().isoformat()}
        elif scope == "context":
            self.context_memory.append({"key": key, "value": value, "timestamp": datetime.now().isoformat()})
            self.context_memory = self.context_memory[-10:]
        else:
            self.user_profile.setdefault("facts", {})[key] = value
            self.pipeline.memory_store.save_memory(
                "fact",
                f"Utilizatorul: {key} = {value}",
                importance=4,
                confidence=0.9,
                topic=self.infer_topic(f"{key} {value}"),
            )
        self._persist()
        return value

    def get_user_fact(self, key: str, default: Any = None, scope: str = "permanent"):
        if scope == "temporary":
            return self.temporary_memory.get(key, {}).get("value", default)
        if scope == "context":
            for item in reversed(self.context_memory):
                if item.get("key") == key:
                    return item.get("value")
            return default
        return self.user_profile.get("facts", {}).get(key, default)

    def record_emotional_event(self, description: str, valence: float = 0.5, tags: Optional[List[str]] = None):
        self._decay_emotions()
        tags = tags or []
        self.user_profile.setdefault("emotional_history", []).append({
            "description": description,
            "valence": float(valence),
            "timestamp": datetime.now().isoformat(),
            "tags": tags,
        })
        self.user_profile["emotional_history"] = self.user_profile["emotional_history"][-20:]

        if valence > 0.7:
            self.emotions.affection = min(1.0, self.emotions.affection + 0.08)
            self.emotions.joy = min(1.0, self.emotions.joy + 0.08)
        elif valence < 0.3:
            self.emotions.irritation = min(1.0, self.emotions.irritation + 0.08)
            self.emotions.sadness = min(1.0, self.emotions.sadness + 0.06)
        else:
            self.emotions.calm = min(1.0, self.emotions.calm + 0.05)

        self.emotions.updated_at = datetime.now().isoformat()
        self._persist()
        return self.emotions.affection

    def detect_user_tone(self, text: str) -> str:
        lowered = self.user_state_detector._normalize(text)

        def contains_phrase(phrase: str) -> bool:
            return bool(re.search(rf"(?<!\w){re.escape(self.user_state_detector._normalize(phrase))}(?!\w)", lowered))

        if any(contains_phrase(k) for k in ["urgent", "important", "trebuie", "problema", "ajutor"]):
            return "serious"
        if any(contains_phrase(k) for k in ["te iubesc", "dragă", "iubire", "frumos", "mă simt bine"]):
            return "affectionate"
        if any(contains_phrase(k) for k in ["furios", "nervos", "iritat", "enervat", "prost"]):
            return "angry"
        if any(contains_phrase(k) for k in ["trist", "tristi", "tristă", "proastă", "rău", "singur", "durere", "nu mai pot", "zi grea"]):
            return "sad"
        if any(contains_phrase(k) for k in ["haha", "glumă", "lol", "😂", "😄", "🤣"]):
            return "playful"
        return "calm"

    def infer_topic(self, text: str) -> str:
        lowered = text.lower()
        keywords = {
            "stress": ["stres", "nu mai pot", "obosit", "greu", "durere", "problema"],
            "love": ["te iubesc", "dragă", "iubire", "iubesc", "mă simt atras"],
            "boredom": ["plictiseală", "nimic", "ma plictisesc", "nu fac nimic"],
            "work": ["job", "muncă", "șef", "colaborator", "team"],
            "health": ["somn", "sănătate", "stres", "durere", "medical"],
            "general": ["chat", "vorbim", "ce faci", "cum ești"],
        }
        for topic, words in keywords.items():
            if any(word in lowered for word in words):
                return topic
        return "general"

    def update_emotions(self, text: str, tone: str):
        self._decay_emotions()
        max_delta = 0.08
        if tone == "angry":
            self.emotions.anger = min(1.0, self.emotions.anger + max_delta)
            self.emotions.cause = "user_anger"
        elif tone == "sad":
            self.emotions.sadness = min(1.0, self.emotions.sadness + max_delta)
            self.emotions.cause = "user_distress"
        elif tone == "affectionate":
            self.emotions.affection = min(1.0, self.emotions.affection + max_delta)
            self.emotions.cause = "affection"
        elif tone == "playful":
            self.emotions.joy = min(1.0, self.emotions.joy + max_delta)
            self.emotions.cause = "playful_conversation"
        else:
            self.emotions.cause = "neutral"

        self.emotions.updated_at = datetime.now().isoformat()
        self._persist()

    def _decay_emotions(self):
        try:
            previous = datetime.fromisoformat(self.emotions.updated_at)
            elapsed_hours = max(0.0, (datetime.now() - previous).total_seconds() / 3600)
        except (TypeError, ValueError):
            elapsed_hours = 0.0
        baselines = {"joy": 0.58, "energy": 0.55, "affection": 0.72, "calm": 0.60, "sadness": 0.12, "irritation": 0.12}
        half_lives = {"joy": 12.0, "energy": 8.0, "affection": 336.0, "calm": 12.0, "sadness": 12.0, "irritation": 12.0}
        for attribute, baseline in baselines.items():
            current = getattr(self.emotions, attribute)
            self.emotions.__setattr__(attribute, baseline + (current - baseline) * (0.5 ** (elapsed_hours / half_lives[attribute])))

    def _describe_emotional_state(self) -> str:
        mood = "senină" if self.emotions.joy > 0.7 else "liniștită" if self.emotions.calm > 0.55 else "mai serioasă"
        energy = "plină de energie" if self.emotions.energy > 0.7 else "cu energie domoală" if self.emotions.energy < 0.35 else "echilibrată"
        affection = "afectuoasă" if self.emotions.affection > 0.65 else "caldă și atentă"
        return f"Ești {mood}, {energy} și {affection}."

    def should_initiate(self, text: str = "", gap_minutes: int = 15) -> bool:
        return self.pipeline.initiative.should_initiate(
            engagement_score=self.pipeline.engagement_score,
            silent_minutes=gap_minutes,
        )

    def update_relationship(self, tone: str):
        if tone in ["affectionate", "playful"]:
            self.relationship.affection = min(1.0, self.relationship.affection + 0.15)
            self.relationship.closeness = min(1.0, self.relationship.closeness + 0.1)
        elif tone == "serious":
            self.relationship.trust = min(1.0, self.relationship.trust + 0.08)
        elif tone == "angry":
            self.relationship.trust = max(0.0, self.relationship.trust - 0.05)
        self._persist()

    def record_episode(self, user_text: str, bot_reply: str, tone: str, topic: Optional[str] = None):
        topic = topic or self.infer_topic(user_text)
        summary = f"Utilizatorul a spus «{user_text[:100]}»; răspunsul a fost în ton {tone}."
        return self.pipeline.memory_store.save_episode(
            summary=summary,
            topic=topic,
            emotion=tone,
            tags=[topic, tone],
        )

    def build_reply(self, user_text: str) -> str:
        user_text = (user_text or "").strip()
        if not user_text:
            return "Scrie-mi ceva și îți răspund."

        command_reply = self._handle_memory_command(user_text)
        if command_reply is not None:
            return command_reply

        tone = self.detect_user_tone(user_text)
        user_state = self.user_state_detector.analyze_message(user_text)
        if tone == "calm" and user_state.emotion in {UserEmotion.SAD, UserEmotion.STRESSED}:
            tone = "sad" if user_state.emotion == UserEmotion.SAD else "serious"

        self.update_emotions(user_text, tone)
        self.update_relationship(tone)

        self.behavior_engine.set_vulgarity_level(self.preferences.vulgarity)
        self.behavior_engine.update_behavior_from_emotions({
            "happiness": self.emotions.joy * 100,
            "affection": self.emotions.affection * 100,
            "energy": self.emotions.energy * 100,
            "irritation": self.emotions.irritation * 100,
        })

        style_profile = self._style_profile_as_dict()
        self.behavior_engine.adapt_to_user_style(user_text, style_profile)

        selected_tone = self.behavior_engine.decide_tone_for_user_input(user_text, user_state.emotion.value)
        if user_state.emotion in {UserEmotion.SAD, UserEmotion.STRESSED}:
            selected_tone = ResponseTone.CONCERNED

        self._ensure_behavior_state()
        self.behavior_engine.current_state.tone = selected_tone

        if selected_tone in {ResponseTone.SERIOUS, ResponseTone.CONCERNED, ResponseTone.DIRECT}:
            self.behavior_engine.current_state.vulgarity_level = VulgarityLevel.CLEAN

        if "azi" in user_text.lower() or "astăzi" in user_text.lower():
            self.remember_user_fact("ziua_actuala", user_text[:80], scope="temporary")

        active_topic = self.pipeline.buffer.topic_for(user_text)
        relevant_episodes = self._relevant_episodes(active_topic)

        user_preferences = self.user_profile.get("preferences", {})
        known_likes = list(dict.fromkeys(
            self.preferences.likes + [str(value) for key, value in user_preferences.items() if key in {"likes", "favorite", "favorite_topic"}]
        ))
        known_dislikes = list(dict.fromkeys(
            self.preferences.dislikes + [str(value) for key, value in user_preferences.items() if key in {"dislikes", "avoid"}]
        ))

        profile_context = []
        user_name = self.get_user_fact("nume") or self.user_profile.get("name")
        if user_name:
            profile_context.append(f"Numele cunoscut al utilizatorului este {user_name}.")
        if known_likes:
            profile_context.append("Preferințe cunoscute: " + ", ".join(known_likes[:4]) + ".")
        if known_dislikes:
            profile_context.append("Subiecte sau lucruri de evitat: " + ", ".join(known_dislikes[:4]) + ".")
        if self.preferences.tone:
            profile_context.append(f"Stilul de ton preferat de utilizator este {self.preferences.tone}.")
        if self.preferences.topics_of_interest:
            profile_context.append("Subiecte preferate: " + ", ".join(self.preferences.topics_of_interest[:4]) + ".")
        if relevant_episodes:
            profile_context.append("Episoade recente relevante: " + " ".join(relevant_episodes[-2:]))

        stage = self.relationship.relationship_stage.replace("_", " ")
        relationship_context = f"Stadiul conversațional al relației este {stage}. "
        relationship_context += "Relația este una de companie virtuală, caldă și fără exclusivitate sau presiune."
        if self.relationship.closeness < 0.3:
            relationship_context += " Păstrează familiaritatea moderată și respectuoasă."
        else:
            relationship_context += " Păstrează căldura fără să presupui intimitate sau dependență."
        if self.relationship.trust >= 0.75:
            relationship_context += " Există încredere construită prin conversații, dar nu presupune acordul utilizatorului."

        behavior_prompt = self.behavior_engine.get_behavior_prompt_injection()
        user_state_prompt = {
            UserEmotion.SAD: "Utilizatorul pare trist; răspunde cu grijă, fără să minimalizezi și fără diagnostic.",
            UserEmotion.STRESSED: "Utilizatorul pare stresat; păstrează tonul calm și oferă pași simpli dacă sunt ceruți.",
            UserEmotion.ANGRY: "Utilizatorul pare supărat; rămâi calmă și clară, fără sarcasm.",
            UserEmotion.HAPPY: "Utilizatorul pare bine dispus; poți răspunde cu energie moderată.",
            UserEmotion.EXCITED: "Utilizatorul pare entuziasmat; întâmpină energia fără să exagerezi.",
        }.get(user_state.emotion, "Adaptează tonul la mesaj fără să presupui stări pe care utilizatorul nu le-a exprimat.")

        legacy_persona = (
            f"Ești {self.bot_name}, un companion virtual calm, cald și inteligent. "
            f"Personalitatea ta: {self.persona.get('signature_mood', 'calmă și atentă')}. "
            f"Tonul detectat: {tone}. {self._describe_emotional_state()} "
            f"{user_state_prompt} {relationship_context} "
            + " ".join(profile_context)
            + "\nInstrucțiuni de comportament:\n"
            + behavior_prompt
            + "\nRăspunde în română, natural și la obiect. Folosește preferințele doar când sunt relevante. "
            "Nu inventa amintiri sau fapte despre utilizator și respectă limitele exprimate."
        )

        reply = self.pipeline.handle_user_message(user_text, persona=legacy_persona)
        if not reply or not str(reply).strip():
            reply = "Momentan nu pot genera un răspuns contextual. Încercăm din nou peste un moment."

        self.record_episode(
            user_text,
            reply,
            tone,
            topic=self.pipeline.buffer.get_current_topic(),
        )
        return reply

    def _handle_memory_command(self, text: str) -> Optional[str]:
        lowered = text.lower()
        if lowered == "/memorie":
            memories = self.pipeline.memory_store.list_memories(limit=20)
            if not memories:
                return "Nu am amintiri salvate."
            return "Amintiri salvate:\n" + "\n".join(f"{row[0]}. [{row[1]}] {row[2]}" for row in memories)

        match = re.fullmatch(r"/uita\s+(\d+)", lowered)
        if match:
            removed = self.pipeline.memory_store.delete_memory(int(match.group(1)))
            return "Am uitat acea amintire." if removed else "Nu am găsit amintirea cu acel ID."

        match = re.fullmatch(r"/corecteaza\s+(\d+)\s+(.+)", text, flags=re.IGNORECASE)
        if match:
            updated = self.pipeline.memory_store.correct_memory(int(match.group(1)), match.group(2).strip())
            return "Am corectat amintirea." if updated else "Nu am găsit amintirea cu acel ID."

        if lowered == "/export":
            return f"Memoria a fost exportată în {self.export_memory()}"

        if lowered == "/sterge confirm":
            self.delete_memory()
            return "Am șters memoria salvată."
        if lowered in {"/sterge", "/șterge"}:
            return "Pentru confirmare, trimite /sterge confirm."
        return None

    def export_memory(self, path: str = "memory_export.json") -> str:
        return self.pipeline.memory_store.export(path)

    def delete_memory(self):
        self.pipeline.memory_store.clear_conversation_data()
        self.preferences = UserPreferences()
        self.relationship = RelationshipState()
        self.emotions = EmotionState()
        self.user_profile = {"name": "", "preferred_name": "dragă", "facts": {}, "preferences": {}, "important_people": [], "plans": [], "birthdays": {}, "emotional_history": []}
        self.temporary_memory = {}
        self.context_memory = []
        self.pipeline.buffer.clear()
        self.pipeline.engagement_score = 0.5
        self.pipeline.initiative.current_level = self.pipeline.initiative.base_level
        self.pipeline.initiative.min_interval_minutes = self.pipeline.initiative.base_min_interval_minutes
        self._persist()

    def remember_preference(self, key: str, value: Any):
        self.preferences.likes = self.preferences.likes if isinstance(self.preferences.likes, list) else []
        self.user_profile.setdefault("preferences", {})[key] = value
        if key in UserPreferences.__dataclass_fields__:
            setattr(self.preferences, key, value)
            if key == "vulgarity":
                self.behavior_engine.set_vulgarity_level(value)
        self.pipeline.memory_store.set_preference(key, value)
        self.pipeline.memory_store.save_memory("preference", f"Preferința utilizatorului: {key} = {value}", 4, 0.9)
        self._persist()
        return value

    def lean_into_persona(self) -> str:
        mood = self.persona.get("signature_mood", "calm, ironica, caldă")
        return f"Eu sunt {self.bot_name}, o persoană {mood}."
