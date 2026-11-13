from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class RecommendationSignalKind(StrEnum):
    DEADLINE = "deadline"
    CONFLICT = "conflict"
    INTERVIEW = "interview"
    FOLLOW_UP = "follow_up"
    AVAILABLE_TIME = "available_time"
    QUIET_HOURS = "quiet_hours"


class RecommendationCode(StrEnum):
    DEADLINE_APPROACHING = "deadline_approaching"
    OVERDUE = "overdue"
    CONFLICT = "conflict"
    INTERVIEW_UPCOMING = "interview_upcoming"
    FOLLOW_UP_DUE = "follow_up_due"
    AVAILABLE_TIME = "available_time"
    QUIET_HOURS = "quiet_hours"


class RecommendationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RecommendationDelivery(StrEnum):
    READY = "ready"
    DEFERRED_QUIET_HOURS = "deferred_quiet_hours"


@dataclass(frozen=True)
class RecommendationSignal:
    kind: RecommendationSignalKind
    reference: str
    title: str
    due_at: datetime | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    priority_score: float = 0.0
    available_minutes: int = 0
    detail: str = ""


@dataclass(frozen=True)
class RecommendationPolicy:
    enabled_codes: frozenset[RecommendationCode] = field(
        default_factory=lambda: frozenset(RecommendationCode)
    )
    deadline_lookahead_days: int = 7
    interview_lookahead_hours: int = 48
    follow_up_lookahead_days: int = 3
    minimum_available_minutes: int = 30
    minimum_priority_score: float = 0.0
    defer_during_quiet_hours: bool = True
    allow_critical_during_quiet_hours: bool = True


@dataclass(frozen=True)
class Recommendation:
    code: RecommendationCode
    severity: RecommendationSeverity
    reference: str
    title: str
    summary: str
    deduplication_key: str
    delivery: RecommendationDelivery
    valid_until: datetime


def generate_recommendations(
    *,
    signals: tuple[RecommendationSignal, ...] | list[RecommendationSignal],
    now: datetime,
    existing_deduplication_keys: frozenset[str] | set[str] = frozenset(),
    policy: RecommendationPolicy | None = None,
) -> tuple[Recommendation, ...]:
    """Generate stable local recommendations without persisting or notifying."""
    _validate_aware(now, "now")
    configured = policy or RecommendationPolicy()
    _validate_policy(configured)
    normalized_now = now.astimezone(UTC)
    normalized_signals = tuple(signals)
    for signal in normalized_signals:
        _validate_signal(signal)
    quiet_until = _active_quiet_hours_until(normalized_signals, normalized_now)
    seen = set(existing_deduplication_keys)
    recommendations: list[Recommendation] = []
    for signal in sorted(normalized_signals, key=_signal_sort_key):
        candidate = _recommend(signal, normalized_now, configured)
        if candidate is None or candidate.code not in configured.enabled_codes:
            continue
        key = _deduplication_key(candidate.code, signal)
        if key in seen:
            continue
        seen.add(key)
        delivery = _delivery(candidate.severity, candidate.code, quiet_until, configured)
        recommendations.append(
            Recommendation(
                code=candidate.code,
                severity=candidate.severity,
                reference=signal.reference,
                title=candidate.title,
                summary=candidate.summary,
                deduplication_key=key,
                delivery=delivery,
                valid_until=candidate.valid_until,
            )
        )
    recommendations.sort(
        key=lambda item: (
            _severity_order(item.severity),
            item.valid_until,
            item.code.value,
            item.reference,
        )
    )
    return tuple(recommendations)


@dataclass(frozen=True)
class _Candidate:
    code: RecommendationCode
    severity: RecommendationSeverity
    title: str
    summary: str
    valid_until: datetime


def _recommend(
    signal: RecommendationSignal,
    now: datetime,
    policy: RecommendationPolicy,
) -> _Candidate | None:
    if signal.kind == RecommendationSignalKind.DEADLINE:
        return _deadline(signal, now, policy)
    if signal.kind == RecommendationSignalKind.CONFLICT:
        return _conflict(signal, now)
    if signal.kind == RecommendationSignalKind.INTERVIEW:
        return _interview(signal, now, policy)
    if signal.kind == RecommendationSignalKind.FOLLOW_UP:
        return _follow_up(signal, now, policy)
    if signal.kind == RecommendationSignalKind.AVAILABLE_TIME:
        return _available_time(signal, now, policy)
    return _quiet_hours(signal, now)


def _deadline(
    signal: RecommendationSignal,
    now: datetime,
    policy: RecommendationPolicy,
) -> _Candidate | None:
    due = signal.due_at.astimezone(UTC)  # type: ignore[union-attr]
    if due < now:
        return _Candidate(
            RecommendationCode.OVERDUE,
            RecommendationSeverity.CRITICAL,
            f"Overdue: {signal.title}",
            f"{signal.title} is overdue and needs review.",
            now + timedelta(days=1),
        )
    if signal.priority_score < policy.minimum_priority_score:
        return None
    remaining = due - now
    if remaining > timedelta(days=policy.deadline_lookahead_days):
        return None
    severity = (
        RecommendationSeverity.WARNING
        if remaining <= timedelta(days=2)
        else RecommendationSeverity.INFO
    )
    return _Candidate(
        RecommendationCode.DEADLINE_APPROACHING,
        severity,
        f"Deadline approaching: {signal.title}",
        f"{signal.title} is due in {_duration_text(remaining)}.",
        due + timedelta(days=1),
    )


def _conflict(signal: RecommendationSignal, now: datetime) -> _Candidate | None:
    end = signal.end_at.astimezone(UTC)  # type: ignore[union-attr]
    if end <= now:
        return None
    return _Candidate(
        RecommendationCode.CONFLICT,
        RecommendationSeverity.CRITICAL,
        f"Schedule conflict: {signal.title}",
        signal.detail or f"{signal.title} overlaps another protected commitment.",
        end,
    )


def _interview(
    signal: RecommendationSignal,
    now: datetime,
    policy: RecommendationPolicy,
) -> _Candidate | None:
    start = signal.start_at.astimezone(UTC)  # type: ignore[union-attr]
    remaining = start - now
    if remaining < timedelta(0) or remaining > timedelta(
        hours=policy.interview_lookahead_hours
    ):
        return None
    return _Candidate(
        RecommendationCode.INTERVIEW_UPCOMING,
        RecommendationSeverity.WARNING,
        f"Interview upcoming: {signal.title}",
        f"{signal.title} starts in {_duration_text(remaining)}.",
        start,
    )


def _follow_up(
    signal: RecommendationSignal,
    now: datetime,
    policy: RecommendationPolicy,
) -> _Candidate | None:
    due = signal.due_at.astimezone(UTC)  # type: ignore[union-attr]
    remaining = due - now
    if remaining > timedelta(days=policy.follow_up_lookahead_days):
        return None
    severity = (
        RecommendationSeverity.CRITICAL
        if remaining < timedelta(0)
        else RecommendationSeverity.WARNING
    )
    return _Candidate(
        RecommendationCode.FOLLOW_UP_DUE,
        severity,
        f"Follow up: {signal.title}",
        (
            f"{signal.title} is overdue."
            if remaining < timedelta(0)
            else f"{signal.title} is due in {_duration_text(remaining)}."
        ),
        max(due, now) + timedelta(days=1),
    )


def _available_time(
    signal: RecommendationSignal,
    now: datetime,
    policy: RecommendationPolicy,
) -> _Candidate | None:
    end = signal.end_at.astimezone(UTC)  # type: ignore[union-attr]
    if end <= now or signal.available_minutes < policy.minimum_available_minutes:
        return None
    return _Candidate(
        RecommendationCode.AVAILABLE_TIME,
        RecommendationSeverity.INFO,
        "Available time",
        f"{signal.available_minutes} minutes are available for flexible work.",
        end,
    )


def _quiet_hours(signal: RecommendationSignal, now: datetime) -> _Candidate | None:
    start = signal.start_at.astimezone(UTC)  # type: ignore[union-attr]
    end = signal.end_at.astimezone(UTC)  # type: ignore[union-attr]
    if not start <= now < end:
        return None
    return _Candidate(
        RecommendationCode.QUIET_HOURS,
        RecommendationSeverity.INFO,
        "Quiet hours are active",
        "Noncritical local recommendations will wait until quiet hours end.",
        end,
    )


def _delivery(
    severity: RecommendationSeverity,
    code: RecommendationCode,
    quiet_until: datetime | None,
    policy: RecommendationPolicy,
) -> RecommendationDelivery:
    if code == RecommendationCode.QUIET_HOURS or quiet_until is None:
        return RecommendationDelivery.READY
    if not policy.defer_during_quiet_hours:
        return RecommendationDelivery.READY
    if severity == RecommendationSeverity.CRITICAL and policy.allow_critical_during_quiet_hours:
        return RecommendationDelivery.READY
    return RecommendationDelivery.DEFERRED_QUIET_HOURS


def _active_quiet_hours_until(
    signals: tuple[RecommendationSignal, ...], now: datetime
) -> datetime | None:
    ends = [
        signal.end_at.astimezone(UTC)
        for signal in signals
        if signal.kind == RecommendationSignalKind.QUIET_HOURS
        and signal.start_at is not None
        and signal.end_at is not None
        and signal.start_at.astimezone(UTC) <= now < signal.end_at.astimezone(UTC)
    ]
    return max(ends, default=None)


def _deduplication_key(
    code: RecommendationCode, signal: RecommendationSignal
) -> str:
    anchor = signal.due_at or signal.start_at or signal.end_at
    anchor_text = anchor.astimezone(UTC).isoformat() if anchor else "unbounded"
    return f"{code.value}:{signal.reference}:{anchor_text}"


def _validate_signal(signal: RecommendationSignal) -> None:
    if not signal.reference.strip() or not signal.title.strip():
        raise ValueError("recommendation signal reference and title must not be blank")
    if not 0 <= signal.priority_score <= 100:
        raise ValueError("priority_score must be between 0 and 100")
    for value, field_name in (
        (signal.due_at, "due_at"),
        (signal.start_at, "start_at"),
        (signal.end_at, "end_at"),
    ):
        if value is not None:
            _validate_aware(value, field_name)
    if signal.kind in {RecommendationSignalKind.DEADLINE, RecommendationSignalKind.FOLLOW_UP}:
        if signal.due_at is None:
            raise ValueError(f"{signal.kind.value} signals require due_at")
    elif signal.kind == RecommendationSignalKind.INTERVIEW:
        if signal.start_at is None:
            raise ValueError("interview signals require start_at")
    else:
        if signal.start_at is None or signal.end_at is None:
            raise ValueError(f"{signal.kind.value} signals require start_at and end_at")
        if signal.end_at <= signal.start_at:
            raise ValueError("signal end_at must be after start_at")
    if signal.kind == RecommendationSignalKind.AVAILABLE_TIME and signal.available_minutes <= 0:
        raise ValueError("available_time signals require positive available_minutes")


def _validate_policy(policy: RecommendationPolicy) -> None:
    if policy.deadline_lookahead_days < 0 or policy.follow_up_lookahead_days < 0:
        raise ValueError("recommendation day lookaheads must not be negative")
    if policy.interview_lookahead_hours < 0:
        raise ValueError("interview_lookahead_hours must not be negative")
    if policy.minimum_available_minutes <= 0:
        raise ValueError("minimum_available_minutes must be positive")
    if not 0 <= policy.minimum_priority_score <= 100:
        raise ValueError("minimum_priority_score must be between 0 and 100")


def _signal_sort_key(signal: RecommendationSignal) -> tuple:
    anchor = signal.due_at or signal.start_at or signal.end_at
    timestamp = anchor.astimezone(UTC).timestamp() if anchor else float("inf")
    return (timestamp, signal.kind.value, signal.reference)


def _severity_order(severity: RecommendationSeverity) -> int:
    return {
        RecommendationSeverity.CRITICAL: 0,
        RecommendationSeverity.WARNING: 1,
        RecommendationSeverity.INFO: 2,
    }[severity]


def _duration_text(value: timedelta) -> str:
    total_minutes = max(0, int(value.total_seconds() // 60))
    days, remaining_minutes = divmod(total_minutes, 1440)
    hours, minutes = divmod(remaining_minutes, 60)
    if days:
        return f"{days} day(s)"
    if hours:
        return f"{hours} hour(s)"
    return f"{minutes} minute(s)"


def _validate_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
