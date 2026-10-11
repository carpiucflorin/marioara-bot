from __future__ import annotations


class ResponsePlanner:
    def decide_length(self, intent: str) -> str:
        mapping = {
            "question": "short",
            "meta": "short",
            "emotional": "medium",
            "playful": "short",
            "story": "long",
            "tool_request": "short",
            "change_topic": "short",
            "topic_opening": "short",
            "continuation": "medium",
            "general": "medium",
        }
        return mapping.get(intent, "medium")

    def decide_temperature(self, intent: str) -> float:
        mapping = {
            "question": 0.4,
            "meta": 0.4,
            "emotional": 0.7,
            "playful": 0.8,
            "story": 0.9,
            "tool_request": 0.2,
            "change_topic": 0.6,
            "topic_opening": 0.7,
            "continuation": 0.65,
            "general": 0.7,
        }
        return mapping.get(intent, 0.7)
