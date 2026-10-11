from __future__ import annotations

import re
from typing import Dict, List


class MemoryExtractor:
    PATTERNS = (
        ("fact", re.compile(r"\b(?:mă cheamă|numele meu este|numele meu e)\s+([^.!?\n]{2,60})", re.IGNORECASE), 4),
        ("fact", re.compile(r"\b(?:locuiesc în|stau în|m-am mutat în)\s+([^.!?\n]{2,80})", re.IGNORECASE), 4),
        ("preference", re.compile(r"\b(?:nu îmi place|nu-mi place|nu imi place|detest)\s+([^.!?\n]{2,100})", re.IGNORECASE), 3),
        ("preference", re.compile(r"(?<!nu )\b(?:îmi place|imi place|prefer)\s+([^.!?\n]{2,100})", re.IGNORECASE), 3),
    )

    def extract(self, text: str, topic: str = "general") -> List[Dict[str, object]]:
        extracted = []
        for kind, pattern, importance in self.PATTERNS:
            match = pattern.search(text or "")
            if not match:
                continue
            detail = " ".join(match.group(1).split()).strip(" ,;:")
            if not detail:
                continue
            prefix = "Preferință" if kind == "preference" else "Fapt despre utilizator"
            extracted.append({
                "kind": kind,
                "text": f"{prefix}: {detail}",
                "importance": importance,
                "confidence": 0.9,
                "topic": topic,
            })
        return extracted

    def persist(self, text: str, topic: str, memory_store) -> int:
        memories = self.extract(text, topic)
        for memory in memories:
            memory_store.save_memory(**memory)
        return len(memories)
