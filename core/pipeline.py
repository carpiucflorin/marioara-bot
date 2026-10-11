from __future__ import annotations

import re
from typing import Callable, Optional

from conversation.coherence_buffer import CoherenceBuffer
from conversation.initiative import InitiativeManager
from core.intent_classifier import IntentClassifier
from core.planner import ResponsePlanner
from core.prompt_builder import PromptBuilder
from core.safety import SafetyGuard
from core.tool_router import LocalToolRouter
from core.background_worker import BackgroundWorker
from memory.extract import MemoryExtractor
from memory.store import MemoryStore


class ChatPipeline:
    def __init__(
        self,
        memory_store: Optional[MemoryStore] = None,
        buffer: Optional[CoherenceBuffer] = None,
        classifier: Optional[IntentClassifier] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        safety: Optional[SafetyGuard] = None,
        initiative: Optional[InitiativeManager] = None,
        reply_generator: Optional[Callable[[str, str, float, int], str]] = None,
    ):
        self.memory_store = memory_store or MemoryStore(db_path="chatbot_memory.db")
        self.buffer = buffer or CoherenceBuffer()
        self.classifier = classifier or IntentClassifier()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.safety = safety or SafetyGuard()
        self.initiative = initiative or InitiativeManager()
        self.planner = ResponsePlanner()
        self.tool_router = LocalToolRouter()
        self.reply_generator = reply_generator
        self.background_worker = BackgroundWorker()
        self.memory_extractor = MemoryExtractor()
        self.session_id = "main"
        self.engagement_score = 0.5
        snapshot = self.memory_store.load_snapshot(self.session_id)
        if snapshot:
            content = snapshot.get("content", {})
            self.buffer.restore(content.get("buffer", {}))
            self.engagement_score = float(content.get("engagement_score", 0.5))
            self.initiative.current_level = float(content.get("initiative_level", self.initiative.base_level))
            self.initiative.min_interval_minutes = int(
                content.get("initiative_min_interval", self.initiative.base_min_interval_minutes)
            )

    def handle_user_message(self, user_message: str, persona: str = "Ești un partener calm și atent.") -> str:
        text = (user_message or "").strip()
        if not text:
            return "Scrie-mi ceva și îți răspund."

        if self.safety.detect_crisis(text):
            self.safety.log_event("crisis_detected", text[:120], "high")
            self.memory_store.log_security_event("crisis_detected", text, "high", "returned_crisis_guidance")
            return self.safety.crisis_reply()

        if self.safety.detect_jailbreak(text):
            self.safety.log_event("jailbreak_attempt", text[:120], "medium")
            self.memory_store.log_security_event("jailbreak_attempt", text, "medium", "blocked_request")
            return self.safety.jailbreak_reply()

        intent = self.classifier.classify_intent(text, self.buffer)
        self.buffer.add_message("user", text)
        self.memory_store.save_message("user", text, intent=intent, planner_type=intent)
        current_topic = self.buffer.get_current_topic()
        self.memory_store.activate_topic(current_topic)
        response_length = self.planner.decide_length(intent)
        reply = self.tool_router.run(text) if intent == "tool_request" else None
        tool_reply = reply is not None

        if reply is None:
            memories = self.memory_store.get_relevant_memories(topic=current_topic, query=text, limit=5)
            recent_messages = self.buffer.get_recent_messages(limit=5)[:-1]
            guidance = self.classifier.get_response_guidance(intent)
            prompt = self.prompt_builder.build_prompt(
                user_message=text,
                persona=persona,
                memories=[row[2] for row in memories],
                recent_messages=recent_messages,
                intent=intent,
                current_topic=current_topic,
                guidance=guidance,
                response_length=response_length,
            )
            if self.reply_generator is None:
                raise RuntimeError("ChatPipeline requires a real reply_generator.")
            temperature = self.planner.decide_temperature(intent)
            max_tokens = 300 if response_length == "long" else 128 if response_length == "short" else 240
            reply = self.reply_generator(prompt, text, temperature, max_tokens)
        if not reply:
            reply = "Nu am primit un răspuns de la Ollama. Verifică dacă serverul și modelul sunt pornite."

        recent = self.memory_store.get_recent_messages(limit=20)
        confidence = self._score_response(reply, response_length, recent)
        if confidence < 0.6 and not tool_reply:
            retry_prompt = (
                prompt
                + "\nCorecție: răspunde direct numai la ultimul mesaj. Nu repeta formulări recente, "
                "nu inventa experiențe reale și încheie în cel mult două propoziții complete."
            )
            reply = self.reply_generator(retry_prompt, text, min(0.5, temperature), max_tokens)
            confidence = self._score_response(reply, response_length, recent)

        filtered_reply = self.safety.filter_response(reply)

        self.memory_store.save_message(
            "assistant",
            filtered_reply,
            intent=intent,
            planner_type=intent,
            confidence_score=confidence,
        )
        self.buffer.add_message("assistant", filtered_reply)

        message_signal = min(1.0, len(text) / 120.0)
        response_signal = min(1.0, len(filtered_reply) / 180.0)
        self.engagement_score = (message_signal + response_signal + 0.5) / 3.0
        self.initiative.update_engagement(self.engagement_score)
        self.memory_store.save_snapshot(
            self.session_id,
            {
                "buffer": self.buffer.serialize(),
                "engagement_score": self.engagement_score,
                "current_topic": current_topic,
                "initiative_level": self.initiative.current_level,
                "initiative_min_interval": self.initiative.min_interval_minutes,
            },
        )
        self.background_worker.enqueue(
            lambda: self.memory_extractor.persist(text, current_topic, self.memory_store),
            priority=1,
        )
        return filtered_reply

    @staticmethod
    def _score_response(reply: str, planned_length: str, recent_messages) -> float:
        words = re.findall(r"[a-zăâîșț0-9]+", (reply or "").lower())
        if not words:
            return 0.0
        score = 0.95
        for opening, closing in (("(", ")"), ("[", "]"), ("{", "}")):
            if reply.count(opening) != reply.count(closing):
                score -= 0.2
        if planned_length == "short" and len(words) > 70:
            score -= 0.4
        elif planned_length == "medium" and len(words) > 220:
            score -= 0.3
        elif planned_length == "long" and len(words) < 5:
            score -= 0.35

        if len(words) >= 7 and planned_length != "short":
            current_phrases = {tuple(words[index:index + 5]) for index in range(len(words) - 4)}
            for row in recent_messages:
                if row[2] != "assistant":
                    continue
                previous_words = re.findall(r"[a-zăâîșț0-9]+", row[3].lower())
                previous_phrases = {tuple(previous_words[index:index + 5]) for index in range(len(previous_words) - 4)}
                if current_phrases & previous_phrases:
                    score -= 0.6
                    break
        return max(0.0, min(1.0, score))

    @staticmethod
    def _fallback_reply(intent: str, text: str = "") -> str:
        topic = (text or "").strip()
        if intent == "topic_opening":
            return (
                f"Subiectul „{topic}” poate fi discutat cu respect și limite clare. "
                "Spune-mi ce aspect concret te interesează."
            )
        if intent == "emotional":
            return (
                "Îmi pare rău că treci printr-un moment greu. Sunt aici să te ascult; "
                "ce te-ar ajuta cel mai mult acum?"
            )
        if intent in {"question", "meta"}:
            return "Nu sunt sigură că am înțeles suficient ca să-ți răspund corect. Poți reformula întrebarea?"
        return "Nu sunt sigură că am înțeles bine. Poți să-mi dai puțin mai mult context?"
