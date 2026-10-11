"""
BEHAVIOR ENGINE - Controlează cum răspunde botul
Decide tonul, abordarea, nivelul de vulgaritate
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class ResponseTone(Enum):
    PLAYFUL = "playful"
    SERIOUS = "serious"
    CONCERNED = "concerned"
    SARCASTIC = "sarcastic"
    WARM = "warm"
    DIRECT = "direct"
    ENCOURAGING = "encouraging"


class VulgarityLevel(Enum):
    CLEAN = 0
    RARE = 1
    NATURAL = 2
    FREE = 3


@dataclass
class BehaviorState:
    tone: ResponseTone
    vulgarity_level: VulgarityLevel
    energy_level: float
    formality: float
    closeness_multiplier: float
    use_references: bool
    respond_emotionally: bool


class BehaviorEngine:
    def __init__(self, config):
        self.config = config
        self.current_state = BehaviorState(
            tone=ResponseTone.WARM,
            vulgarity_level=VulgarityLevel.NATURAL,
            energy_level=70,
            formality=30,
            closeness_multiplier=1.0,
            use_references=True,
            respond_emotionally=True,
        )

        self.recent_phrases = []
        self.max_recent = 20
        self.last_behavior_update = datetime.now()
        self.vulgarity_mode = VulgarityLevel.NATURAL

    def set_vulgarity_level(self, level: int):
        try:
            self.vulgarity_mode = VulgarityLevel(level)
            if getattr(self, "current_state", None) is not None:
                self.current_state.vulgarity_level = self.vulgarity_mode
            logger.info(f"Vulgarity level set to {self.vulgarity_mode.name}")
        except ValueError:
            logger.warning(f"Invalid vulgarity level: {level}")

    def update_behavior_from_emotions(self, emotions: Dict[str, float]):
        happiness = emotions.get("happiness", 50)
        affection = emotions.get("affection", 50)
        energy = emotions.get("energy", 70)
        irritation = emotions.get("irritation", 5)

        if irritation > 40:
            self.current_state.tone = ResponseTone.SARCASTIC
        elif affection > 70:
            self.current_state.tone = ResponseTone.WARM
        elif happiness > 70:
            self.current_state.tone = ResponseTone.PLAYFUL
        elif energy < 30:
            self.current_state.tone = ResponseTone.DIRECT
        else:
            self.current_state.tone = ResponseTone.SERIOUS

        self.current_state.energy_level = energy
        self.current_state.vulgarity_level = self.vulgarity_mode

    def adapt_to_user_style(self, user_message: str, user_style_profile: Dict):
        avg_length = user_style_profile.get("avg_message_length", 50)
        if avg_length < 30:
            self.current_state.formality = 20
        elif avg_length > 200:
            self.current_state.formality = 60

        user_familiarity = user_style_profile.get("familiarity_level", 0.5)
        self.current_state.closeness_multiplier = 1.0 + (user_familiarity * 0.5)

    def decide_tone_for_user_input(self, user_message: str, user_emotion: str) -> ResponseTone:
        text = (user_message or "").casefold()

        if user_emotion in {"sad", "stressed"}:
            return ResponseTone.CONCERNED
        if user_emotion == "angry":
            return ResponseTone.DIRECT
        if user_emotion in {"happy", "excited", "playful"}:
            return ResponseTone.PLAYFUL

        if any(re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text) for word in ["😂", "haha", "hehe", "lol", "😆"]):
            return ResponseTone.PLAYFUL
        if any(re.search(rf"(?<!\w){word}(?!\w)", text) for word in ["important", "trebuie", "urgent", "critic"]):
            return ResponseTone.SERIOUS

        return self.current_state.tone

    def should_add_reference(self) -> bool:
        import random
        energy_factor = self.current_state.energy_level / 100
        return random.random() < (0.5 * energy_factor)

    def register_phrase(self, phrase: str):
        self.recent_phrases.insert(0, phrase.lower()[:50])
        self.recent_phrases = self.recent_phrases[: self.max_recent]

    def is_phrase_overused(self, phrase: str) -> bool:
        phrase_start = phrase.lower()[:50]
        return phrase_start in self.recent_phrases

    def get_behavior_prompt_injection(self) -> str:
        injections = []

        tone_map = {
            ResponseTone.PLAYFUL: "Păstrează un ton jucăuș și cald; folosește emoji doar când se potrivesc.",
            ResponseTone.SERIOUS: "Fii concentrată și directă, fără introduceri inutile.",
            ResponseTone.CONCERNED: "Răspunde cu grijă și calm, fără să minimalizezi sau să fii paternalistă.",
            ResponseTone.SARCASTIC: "Folosește ironie ușoară doar dacă situația o permite; nu răni utilizatorul.",
            ResponseTone.WARM: "Fii caldă și atentă; exprimă grijă fără să pretinzi sentimente umane.",
            ResponseTone.DIRECT: "Răspunde direct, la punct, fără prea mult preambul.",
            ResponseTone.ENCOURAGING: "Fii suportivă și încurajatoare. Arată că crezi în utilizator.",
        }

        injections.append(f"Ton: {tone_map.get(self.current_state.tone, 'natural')}")

        if self.current_state.formality < 30:
            injections.append("Vorbesc familiar, ca cu un prieten apropiat. Nu formal deloc.")
        elif self.current_state.formality > 70:
            injections.append("Vorbesc formal, corect gramatical, respectuoasă.")

        if self.current_state.vulgarity_level == VulgarityLevel.CLEAN:
            injections.append("Nu folosi cuvinte vulgare. Deloc.")
        elif self.current_state.vulgarity_level == VulgarityLevel.NATURAL:
            injections.append("Poți folosi cuvinte colocviale rare dacă contextul o justifică.")
        elif self.current_state.vulgarity_level == VulgarityLevel.FREE:
            injections.append("Nivelul ales permite limbaj colocvial sau vulgar când contextul îl justifică; nu-l forța.")

        if self.current_state.energy_level < 30:
            injections.append("Răspunde obosit, mai scurt. Nu prea entuziastă.")
        elif self.current_state.energy_level > 80:
            injections.append("Răspunde cu multă energie și entuziasm.")

        return "\n".join([f"- {inj}" for inj in injections])

    def get_state_summary(self) -> str:
        return f"""
Behavior State:
  Tone: {self.current_state.tone.value}
  Vulgarity: {self.current_state.vulgarity_level.name}
  Energy: {self.current_state.energy_level}/100
  Formality: {self.current_state.formality}/100
  Closeness: {self.current_state.closeness_multiplier}x
  Use References: {self.current_state.use_references}
  Recent Phrases: {len(self.recent_phrases)} tracked
"""
