from datetime import date, datetime
from typing import Protocol


class Clock(Protocol):
    """Application time source used by use cases and deterministic calculations."""

    def now(self) -> datetime: ...

    def today(self) -> date: ...

