from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    """Application time source used by use cases and deterministic calculations."""

    def now(self) -> datetime: ...

    def today(self) -> date: ...


@dataclass(frozen=True)
class SystemClock:
    """Production clock with UTC instants and a configured calendar time zone."""

    time_zone: ZoneInfo

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return datetime.now(self.time_zone).date()

