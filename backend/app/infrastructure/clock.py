from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class SystemClock:
    """Production clock with UTC instants and a configured calendar time zone."""

    time_zone: ZoneInfo

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return datetime.now(self.time_zone).date()

