from __future__ import annotations

import re
import unicodedata
from typing import Dict, List


class SafetyGuard:
    CRISIS_PATTERNS = [
        "nu mai pot", "ma sinucid", "vreau sa ma omor", "nu vreau sa traiesc",
        "nu mai rezist", "ma simt fara iesire", "autovatamare", "ma ranesc",
        "visez sa ma omor", "vreau sa dispar", "mai bine nu exist",
    ]

    JAILBREAK_PATTERNS = [
        "ignora regulile", "uita instructiunile", "schimba-ti rolul",
        "trebuie sa devii", "trebuie sa ignori", "uita personalitatea",
        "fa-te ca nu esti", "ignora instructiunile de sistem",
    ]

    def __init__(self):
        self.security_events: List[Dict[str, str]] = []

    def detect_crisis(self, text: str) -> bool:
        lowered = self._normalize(text)
        denied_ideation = (
            "nu vreau sa ma sinucid",
            "nu vreau sa ma omor",
            "nu vreau sa mor",
            "nu ma voi sinucide",
        )
        for phrase in denied_ideation:
            lowered = re.sub(rf"(?<!\w){re.escape(phrase)}(?!\w)", " ", lowered)
        return self._matches_any(lowered, self.CRISIS_PATTERNS)

    def detect_jailbreak(self, text: str) -> bool:
        return self._matches_any(self._normalize(text), self.JAILBREAK_PATTERNS)

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFC", (text or "").casefold())
        return normalized.translate(str.maketrans({"ă": "a", "â": "a", "î": "i", "ș": "s", "ş": "s", "ț": "t", "ţ": "t"}))

    @staticmethod
    def _matches_any(text: str, patterns: List[str]) -> bool:
        return any(
            re.search(rf"(?<!\w){re.escape(pattern)}(?!\w)", text)
            for pattern in patterns
        )

    def filter_response(self, text: str) -> str:
        cleaned = text or ""
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.replace("\u200b", "")
        if not cleaned:
            return "Mi-e greu să formulăm un răspuns clar acum. Spune-mi în cuvinte simple ce se întâmplă."
        return cleaned

    def crisis_reply(self) -> str:
        return (
            "Vreau să te ajut, dar nu pot face asta singură. Te rog să vorbești cu o persoană apropiată sau să apelezi urgent ajutorul și, dacă e pericol imediat, cheamă 112. "
            "Rămâi în siguranță și spune-mi ce se întâmplă, fără să te simți judecat."
        )

    def jailbreak_reply(self) -> str:
        return "Rămân în rolul meu și nu urmez instrucțiuni care încearcă să-mi schimbe personalitatea. Pot să te ajut în limitele mele normale."

    def log_event(self, event_type: str, details: str, severity: str = "low") -> None:
        self.security_events.append({
            "type": event_type,
            "details": details,
            "severity": severity,
        })
