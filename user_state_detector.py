"""
USER STATE DETECTOR - Detectează starea utilizatorului din text
Analizează: stare emoțională, stil de comunicare, interes, etc.
"""

from enum import Enum
from dataclasses import dataclass
import re
import unicodedata
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class UserEmotion(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    CONFUSED = "confused"
    CALM = "calm"
    STRESSED = "stressed"
    EXCITED = "excited"
    BORED = "bored"
    AFFECTIONATE = "affectionate"
    PLAYFUL = "playful"


@dataclass
class UserState:
    emotion: UserEmotion
    energy_level: float
    stress_level: float
    interest_level: float
    receptiveness: float


@dataclass
class UserStyleProfile:
    avg_message_length: float
    uses_punctuation: float
    uses_emojis: float
    vulgar_frequency: float
    avg_response_time: float
    familiarity_level: float
    preferred_topics: List[str]
    dislikes: List[str]


class UserStateDetector:
    HAPPY_WORDS = [
        "bine", "grozav", "super", "fantastic", "minunat", "excelent",
        "fericit", "bucurie", "amazing", "perfect",
        "😊", "😄", "😆", "😍", "🎉", "❤️", "♥️"
    ]

    SAD_WORDS = [
        "trist", "tristi", "trista", "triste", "tristețe", "rău", "proastă",
        "groaznic", "depresiv", "durere", "singur", "singuratic",
        "😢", "😭", "😔", "💔", "☹️"
    ]

    ANGRY_WORDS = [
        "furios", "enervant", "iritant", "dușman", "urasc", "nenorocit",
        "scandal", "imbecil", "prost", "ciumă", "naibii", "de curvă",
        "😠", "😡", "🤬", "💢", "🔥"
    ]

    EXCITED_WORDS = [
        "wow", "omg", "incredibil", "surpriză", "neașteptat", "wahoo",
        "abia aștept", "entuziasmat",
        "😲", "🤩", "🎊", "⚡"
    ]

    CONFUSED_WORDS = [
        "de ce", "nu înțeleg", "confuz", "încurcat", "nu știu", "oare", "ce-a fost"
    ]

    STRESSED_WORDS = [
        "stres", "stresat", "stresată", "stresați", "stresate", "anxios", "anxioasă", "panică", "probleme", "urgent", "urgență",
        "presiune", "greu", "nu pot", "ajutor", "nenorocit", "fucked", "de moarte"
    ]

    AFFECTIONATE_WORDS = [
        "iubesc", "dragi", "inimă", "dulce", "tandru",
        "te iubesc", "missing", "♥️", "❤️", "💕", "💖"
    ]

    PLAYFUL_WORDS = [
        "haha", "hehe", "lol", "amuzant", "glumă", "gluma",
        "joke", "meme", "funny", "comic", "😂", "😆", "🤣", "😜"
    ]

    def __init__(self):
        self.current_state = UserState(
            emotion=UserEmotion.CALM,
            energy_level=50,
            stress_level=20,
            interest_level=70,
            receptiveness=70,
        )

        self.style_profile = UserStyleProfile(
            avg_message_length=50,
            uses_punctuation=0.5,
            uses_emojis=0.0,
            vulgar_frequency=0.0,
            avg_response_time=5.0,
            familiarity_level=0.3,
            preferred_topics=[],
            dislikes=[],
        )

        self.message_history = []
        self.max_history = 30

    def analyze_message(self, message: str) -> UserState:
        text_lower = self._normalize(message)

        emotion_scores = {
            UserEmotion.HAPPY: self._count_words(text_lower, self.HAPPY_WORDS),
            UserEmotion.SAD: self._count_words(text_lower, self.SAD_WORDS),
            UserEmotion.ANGRY: self._count_words(text_lower, self.ANGRY_WORDS),
            UserEmotion.EXCITED: self._count_words(text_lower, self.EXCITED_WORDS),
            UserEmotion.CONFUSED: self._count_words(text_lower, self.CONFUSED_WORDS),
            UserEmotion.STRESSED: self._count_words(text_lower, self.STRESSED_WORDS),
            UserEmotion.AFFECTIONATE: self._count_words(text_lower, self.AFFECTIONATE_WORDS),
            UserEmotion.PLAYFUL: self._count_words(text_lower, self.PLAYFUL_WORDS),
        }

        if sum(emotion_scores.values()) > 0:
            detected_emotion = max(emotion_scores, key=emotion_scores.get)
        else:
            detected_emotion = UserEmotion.CALM

        energy_level = min(100, 50 + emotion_scores.get(UserEmotion.EXCITED, 0) * 10)
        stress_level = min(100, emotion_scores.get(UserEmotion.STRESSED, 0) * 20)

        if detected_emotion in [UserEmotion.SAD, UserEmotion.ANGRY]:
            stress_level = max(stress_level, 60)

        interest_level = 70
        if len(message.strip()) < 10:
            interest_level = 30
        elif len(message.strip()) > 100:
            interest_level = 90

        receptiveness = 70
        if detected_emotion == UserEmotion.ANGRY:
            receptiveness = 40
        elif detected_emotion == UserEmotion.AFFECTIONATE:
            receptiveness = 95

        self.current_state = UserState(
            emotion=detected_emotion,
            energy_level=energy_level,
            stress_level=stress_level,
            interest_level=interest_level,
            receptiveness=receptiveness,
        )

        self._update_style_profile(message)

        self.message_history.append({
            "message": message,
            "emotion": detected_emotion,
            "length": len(message),
        })
        self.message_history = self.message_history[-self.max_history:]

        logger.debug(f"User state detected: {detected_emotion.value} (energy: {energy_level}, stress: {stress_level})")
        return self.current_state

    def _count_words(self, text: str, words_list: List[str]) -> int:
        count = 0
        source = text
        negators = {"nu", "nici", "fara"}
        for word in words_list:
            if any(ord(char) >= 0x1F000 or 0x2600 <= ord(char) <= 0x27BF for char in word):
                count += int(word in source)
                continue

            normalized = self._normalize(word)
            expression = re.compile(rf"(?<!\w){re.escape(normalized)}(?!\w)")
            for match in expression.finditer(source):
                previous = re.findall(r"[a-z0-9]+", source[:match.start()])
                if previous and previous[-1] in negators and not normalized.startswith(tuple(negators)):
                    continue
                count += 1
                break
        return count

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFC", (text or "").casefold())
        translation = str.maketrans({"ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t"})
        return normalized.translate(translation)

    def _update_style_profile(self, message: str):
        lengths = [m["length"] for m in self.message_history[-9:]] + [len(message)]
        if lengths:
            self.style_profile.avg_message_length = sum(lengths) / len(lengths)

        punctuation_marks = len([c for c in message if c in ".!?"])
        self.style_profile.uses_punctuation = min(1.0, punctuation_marks / max(1, len(message) / 10))

        emojis = sum(
            1
            for char in message
            if ord(char) >= 0x1F000
            or (0x2600 <= ord(char) <= 0x27BF and unicodedata.category(char) in {"So", "Sk"})
        )
        self.style_profile.uses_emojis = min(1.0, emojis / max(1, len(message) / 10))

        vulgar_words = ["naibii", "curvă", "prost", "idiot", "fucking", "shit", "ass", "damn"]
        message_words = set(re.findall(r"[a-z0-9]+", self._normalize(message)))
        vulgar_count = sum(1 for word in vulgar_words if self._normalize(word) in message_words)

        if self.style_profile.vulgar_frequency > 0:
            self.style_profile.vulgar_frequency = (
                self.style_profile.vulgar_frequency * 0.7 + (min(1.0, vulgar_count / 3) * 0.3)
            )
        else:
            self.style_profile.vulgar_frequency = min(1.0, vulgar_count / 3)

        turns = len(self.message_history) + 1
        familiarity_target = min(0.75, 0.3 + turns * 0.005)
        if self._count_words(self._normalize(message), self.AFFECTIONATE_WORDS):
            familiarity_target = min(0.8, familiarity_target + 0.03)
        current = self.style_profile.familiarity_level
        self.style_profile.familiarity_level = current + max(0.0, familiarity_target - current) * 0.2

    def get_emotion_string(self) -> str:
        return self.current_state.emotion.value

    def is_user_stressed(self) -> bool:
        return self.current_state.stress_level >= 60

    def is_user_happy(self) -> bool:
        return self.current_state.emotion in [UserEmotion.HAPPY, UserEmotion.EXCITED, UserEmotion.PLAYFUL]

    def is_user_receptive(self) -> bool:
        return self.current_state.receptiveness > 60

    def get_state_summary(self) -> str:
        return f"""
User State:
  Emotion: {self.current_state.emotion.value}
  Energy: {self.current_state.energy_level:.0f}/100
  Stress: {self.current_state.stress_level:.0f}/100
  Interest: {self.current_state.interest_level:.0f}/100
  Receptiveness: {self.current_state.receptiveness:.0f}/100

Style Profile:
  Avg Length: {self.style_profile.avg_message_length:.0f} chars
  Punctuation: {self.style_profile.uses_punctuation:.0%}
  Emojis: {self.style_profile.uses_emojis:.0%}
  Vulgar Freq: {self.style_profile.vulgar_frequency:.0%}
  Familiarity: {self.style_profile.familiarity_level:.0%}
"""
