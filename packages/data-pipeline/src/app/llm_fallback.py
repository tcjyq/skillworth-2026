from __future__ import annotations

from typing import Protocol


class LLMSkillExtractor(Protocol):
    @property
    def enabled(self) -> bool: ...

    def extract(self, text: str) -> list[str]: ...


class DisabledLLMSkillExtractor:
    """Default no-op implementation: no API calls, credentials, or network access."""

    @property
    def enabled(self) -> bool:
        return False

    def extract(self, text: str) -> list[str]:
        return []

