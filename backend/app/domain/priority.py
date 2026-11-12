from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from enum import StrEnum


class ResponsibilityKind(StrEnum):
    TASK = "task"
    EVENT = "event"
    DEADLINE = "deadline"
    APPLICATION = "application"
    FOLLOW_UP = "follow_up"


class PriorityReasonCode(StrEnum):
    COMPLETED = "completed"
    IMPORTANCE = "importance"
    OVERDUE = "overdue"
    DUE_TODAY = "due_today"
    DUE_SOON = "due_soon"
    UPCOMING = "upcoming"
    LONG_RANGE = "long_range"
    NO_DEADLINE = "no_deadline"
    QUICK_WIN = "quick_win"
    LARGE_EFFORT = "large_effort"
    FIXED_COMMITMENT = "fixed_commitment"
    APPLICATION_ACTIVE = "application_active"
    APPLICATION_INTERVIEWING = "application_interviewing"
    APPLICATION_OFFER = "application_offer"
    SCORE_CAP = "score_cap"


@dataclass(frozen=True)
class PriorityWeights:
    importance_per_level: float = 10.0
    overdue: float = 45.0
    due_today: float = 40.0
    due_within_two_days: float = 32.0
    due_within_week: float = 22.0
    due_within_month: float = 12.0
    long_range: float = 4.0
    quick_win: float = 5.0
    large_effort: float = -5.0
    fixed_commitment: float = 5.0
    application_active: float = 3.0
    application_interviewing: float = 12.0
    application_offer: float = 15.0
    quick_win_max_minutes: int = 30
    large_effort_min_minutes: int = 240


@dataclass(frozen=True)
class PriorityInput:
    kind: ResponsibilityKind
    importance: int
    due_at: datetime | None
    estimated_minutes: int
    is_completed: bool = False
    is_fixed: bool = False
    application_status: str | None = None


@dataclass(frozen=True)
class PriorityComponent:
    code: PriorityReasonCode
    points: float
    detail: str


@dataclass(frozen=True)
class PriorityResult:
    score: float
    components: tuple[PriorityComponent, ...]

    @property
    def reason_codes(self) -> list[str]:
        return [component.code.value for component in self.components]

    @property
    def reasons(self) -> list[str]:
        return [component.detail for component in self.components]


def calculate_responsibility_priority(
    responsibility: PriorityInput,
    *,
    now: datetime,
    weights: PriorityWeights | None = None,
) -> PriorityResult:
    """Calculate a deterministic priority from explicit inputs and time."""
    _validate_input(responsibility, now)
    configured = weights or PriorityWeights()
    if responsibility.is_completed:
        return PriorityResult(
            score=0.0,
            components=(
                PriorityComponent(
                    PriorityReasonCode.COMPLETED,
                    0.0,
                    f"{responsibility.kind.value.replace('_', ' ').title()} is complete.",
                ),
            ),
        )

    components = [
        PriorityComponent(
            PriorityReasonCode.IMPORTANCE,
            responsibility.importance * configured.importance_per_level,
            (
                f"Importance {responsibility.importance}/5 contributes "
                f"{_points(responsibility.importance * configured.importance_per_level)} points."
            ),
        )
    ]
    components.append(_urgency_component(responsibility.due_at, now, configured))

    if 0 < responsibility.estimated_minutes <= configured.quick_win_max_minutes:
        components.append(
            PriorityComponent(
                PriorityReasonCode.QUICK_WIN,
                configured.quick_win,
                f"A short item adds {_points(configured.quick_win)} quick-win points.",
            )
        )
    elif responsibility.estimated_minutes > configured.large_effort_min_minutes:
        components.append(
            PriorityComponent(
                PriorityReasonCode.LARGE_EFFORT,
                configured.large_effort,
                (
                    f"A large item contributes {_points(configured.large_effort)} points "
                    "until it can be broken down or scheduled."
                ),
            )
        )

    if responsibility.is_fixed:
        components.append(
            PriorityComponent(
                PriorityReasonCode.FIXED_COMMITMENT,
                configured.fixed_commitment,
                f"A fixed commitment adds {_points(configured.fixed_commitment)} points.",
            )
        )
    application_component = _application_component(
        responsibility.application_status, configured
    )
    if application_component is not None:
        components.append(application_component)

    raw_score = round(sum(component.points for component in components), 1)
    bounded_score = round(max(0.0, min(raw_score, 100.0)), 1)
    if bounded_score != raw_score:
        adjustment = round(bounded_score - raw_score, 1)
        components.append(
            PriorityComponent(
                PriorityReasonCode.SCORE_CAP,
                adjustment,
                f"The score boundary adjusts the total by {_points(adjustment)} points.",
            )
        )
    return PriorityResult(score=bounded_score, components=tuple(components))


def calculate_priority(
    *,
    importance: int,
    due_date: date | None,
    estimated_minutes: int,
    is_completed: bool,
    today: date,
    weights: PriorityWeights | None = None,
) -> PriorityResult:
    """Compatibility adapter for task callers using local calendar dates."""
    due_at = (
        datetime.combine(due_date, time.max, tzinfo=UTC) if due_date is not None else None
    )
    return calculate_responsibility_priority(
        PriorityInput(
            kind=ResponsibilityKind.TASK,
            importance=importance,
            due_at=due_at,
            estimated_minutes=estimated_minutes,
            is_completed=is_completed,
        ),
        now=datetime.combine(today, time.min, tzinfo=UTC),
        weights=weights,
    )


def _validate_input(responsibility: PriorityInput, now: datetime) -> None:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not 1 <= responsibility.importance <= 5:
        raise ValueError("importance must be between 1 and 5")
    if responsibility.estimated_minutes < 0:
        raise ValueError("estimated_minutes must not be negative")
    if responsibility.due_at is not None and (
        responsibility.due_at.tzinfo is None
        or responsibility.due_at.utcoffset() is None
    ):
        raise ValueError("due_at must be timezone-aware")


def _urgency_component(
    due_at: datetime | None, now: datetime, weights: PriorityWeights
) -> PriorityComponent:
    if due_at is None:
        return PriorityComponent(
            PriorityReasonCode.NO_DEADLINE, 0.0, "No deadline pressure was added."
        )
    local_due = due_at.astimezone(now.tzinfo)
    days_remaining = (local_due.date() - now.date()).days
    if due_at < now:
        return PriorityComponent(
            PriorityReasonCode.OVERDUE,
            weights.overdue,
            (
                f"Overdue by {max(1, abs(days_remaining))} day(s) adds "
                f"{_points(weights.overdue)} points."
            ),
        )
    if days_remaining == 0:
        return PriorityComponent(
            PriorityReasonCode.DUE_TODAY,
            weights.due_today,
            f"Due today adds {_points(weights.due_today)} points.",
        )
    if days_remaining <= 2:
        return PriorityComponent(
            PriorityReasonCode.DUE_SOON,
            weights.due_within_two_days,
            f"Due in {days_remaining} day(s) adds {_points(weights.due_within_two_days)} points.",
        )
    if days_remaining <= 7:
        return PriorityComponent(
            PriorityReasonCode.UPCOMING,
            weights.due_within_week,
            (
                f"Due within a week adds {_points(weights.due_within_week)} points "
                f"({days_remaining} days remain)."
            ),
        )
    if days_remaining <= 30:
        return PriorityComponent(
            PriorityReasonCode.UPCOMING,
            weights.due_within_month,
            (
                f"Due within a month adds {_points(weights.due_within_month)} points "
                f"({days_remaining} days remain)."
            ),
        )
    return PriorityComponent(
        PriorityReasonCode.LONG_RANGE,
        weights.long_range,
        (
            f"Long-range deadline adds {_points(weights.long_range)} points "
            f"({days_remaining} days remain)."
        ),
    )


def _application_component(
    status: str | None, weights: PriorityWeights
) -> PriorityComponent | None:
    if status is None:
        return None
    normalized = status.casefold()
    if normalized == "interviewing":
        return PriorityComponent(
            PriorityReasonCode.APPLICATION_INTERVIEWING,
            weights.application_interviewing,
            f"Interviewing adds {_points(weights.application_interviewing)} points.",
        )
    if normalized == "offer":
        return PriorityComponent(
            PriorityReasonCode.APPLICATION_OFFER,
            weights.application_offer,
            f"An active offer adds {_points(weights.application_offer)} points.",
        )
    if normalized in {"saved", "preparing", "applied"}:
        return PriorityComponent(
            PriorityReasonCode.APPLICATION_ACTIVE,
            weights.application_active,
            f"An active application adds {_points(weights.application_active)} points.",
        )
    return None


def _points(value: float) -> str:
    return f"{value:g}"

