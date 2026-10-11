from __future__ import annotations

import re


class IntentClassifier:
    def classify_intent(self, text: str, context=None) -> str:
        lowered = (text or "").lower()

        if not lowered:
            return "general"

        if any(word in lowered for word in ["calculează", "calculeaza", "calcul", "cât face", "cat face", "adună", "scade", "ce dată", "data de azi", "ce oră", "cât e ceasul", "vremea", "calendar"]):
            return "tool_request"

        if re.search(r"\d\s*[+*/%-]\s*\d", lowered):
            return "tool_request"

        if any(word in lowered for word in ["povestește-mi", "povesteste-mi", "scrie o poveste", "inventează o poveste", "inventeaza o poveste"]):
            return "story"

        if any(word in lowered for word in ["vorbim despre", "hai să vorbim", "mă interesează", "vreau să discutăm", "vrem să vorbim"]):
            return "change_topic"

        if lowered.startswith("despre ") and "?" not in lowered and len(lowered.split()) <= 6:
            return "topic_opening"

        if any(word in lowered for word in ["cine ești", "cine esti", "ce știi despre mine", "ce stii despre mine", "îți amintești", "iti amintesti", "cum funcționezi", "cum functionezi"]):
            return "meta"

        if lowered.startswith(("ce ", "cine ", "unde ", "când ", "cand ", "cum ", "de ce ", "care ", "cât ", "cat ")) or "?" in lowered:
            return "question"

        if any(word in lowered for word in ["ajutor", "problema", "stres", "rău", "trist", "supărat", "nu mai pot"]):
            return "emotional"

        if any(word in lowered for word in ["glumă", "gluma", "haha", "lol", "joke", "faceți o glumă"]):
            return "playful"

        if any(word in lowered for word in ["te iubesc", "dragă", "iubire", "afecțiune", "mă simt", "îmi place"]):
            return "emotional"

        if context and getattr(context, "messages", None):
            return "continuation"

        return "general"

    def get_response_guidance(self, intent: str) -> str:
        guidance = {
            "question": "Răspunde direct, clar și concis.",
            "meta": "Răspunde sincer despre identitate, memorie și limite; nu pretinde că ești om.",
            "emotional": "Validare caldă, sprijin și un follow-up natural.",
            "playful": "Răspuns ușor, jucăuș și cu zâmbet.",
            "tool_request": "Răspuns precis, fără jargon și cu concluzie clară.",
            "story": "Spune povestea cerută direct, cu început, desfășurare și încheiere.",
            "change_topic": "Primește schimbarea de subiect fără să forțezi revenirea la cel vechi.",
            "topic_opening": "Recunoaște subiectul propus și întreabă ce aspect concret dorește utilizatorul să discute.",
            "continuation": "Continuă subiectul activ folosind contextul relevant, fără să reiei introducerea.",
            "general": "Răspuns natural, scurt și conversațional.",
        }
        return guidance.get(intent, guidance["general"])
