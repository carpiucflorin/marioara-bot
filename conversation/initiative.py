from __future__ import annotations


class InitiativeManager:
    def __init__(self, base_level: float = 0.4, base_min_interval_minutes: int = 20):
        self.base_level = base_level
        self.current_level = base_level
        self.base_min_interval_minutes = base_min_interval_minutes
        self.min_interval_minutes = base_min_interval_minutes

    def update_engagement(self, score: float):
        self.current_level = max(0.0, min(1.0, score))

    def should_initiate(self, engagement_score: float, silent_minutes: int = 15) -> bool:
        if silent_minutes < self.min_interval_minutes:
            return False
        return engagement_score >= 0.75 or self.current_level >= 0.8
