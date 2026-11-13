from datetime import UTC, datetime

from app.domain.recommendations import (
    RecommendationCode,
    RecommendationDelivery,
    RecommendationPolicy,
    RecommendationSignal,
    RecommendationSignalKind,
    generate_recommendations,
)


def at(day: int, hour: int = 12) -> datetime:
    return datetime(2026, 11, day, hour, tzinfo=UTC)


def test_rules_cover_deadlines_overdue_conflicts_interviews_and_followups() -> None:
    recommendations = generate_recommendations(
        now=at(10),
        signals=[
            RecommendationSignal(
                RecommendationSignalKind.DEADLINE,
                "task:soon",
                "Fictional deadline",
                due_at=at(11),
                priority_score=80,
            ),
            RecommendationSignal(
                RecommendationSignalKind.DEADLINE,
                "task:overdue",
                "Fictional overdue task",
                due_at=at(9),
            ),
            RecommendationSignal(
                RecommendationSignalKind.CONFLICT,
                "conflict:one",
                "Fictional overlap",
                start_at=at(10, 13),
                end_at=at(10, 14),
            ),
            RecommendationSignal(
                RecommendationSignalKind.INTERVIEW,
                "interview:one",
                "Fictional interview",
                start_at=at(11, 9),
            ),
            RecommendationSignal(
                RecommendationSignalKind.FOLLOW_UP,
                "follow-up:one",
                "Fictional thank-you note",
                due_at=at(12),
            ),
        ],
    )

    assert {item.code for item in recommendations} == {
        RecommendationCode.DEADLINE_APPROACHING,
        RecommendationCode.OVERDUE,
        RecommendationCode.CONFLICT,
        RecommendationCode.INTERVIEW_UPCOMING,
        RecommendationCode.FOLLOW_UP_DUE,
    }
    assert recommendations[0].code in {
        RecommendationCode.OVERDUE,
        RecommendationCode.CONFLICT,
    }


def test_available_time_threshold_and_batch_deduplication() -> None:
    repeated = RecommendationSignal(
        RecommendationSignalKind.AVAILABLE_TIME,
        "availability:morning",
        "Fictional open block",
        start_at=at(10, 13),
        end_at=at(10, 14),
        available_minutes=60,
    )
    first = generate_recommendations(now=at(10), signals=[repeated, repeated])
    assert len(first) == 1
    assert first[0].code == RecommendationCode.AVAILABLE_TIME

    second = generate_recommendations(
        now=at(10),
        signals=[repeated],
        existing_deduplication_keys={first[0].deduplication_key},
    )
    assert second == ()

    below_threshold = generate_recommendations(
        now=at(10),
        signals=[
            RecommendationSignal(
                RecommendationSignalKind.AVAILABLE_TIME,
                "availability:short",
                "Short fictional block",
                start_at=at(10, 13),
                end_at=at(10, 14),
                available_minutes=15,
            )
        ],
        policy=RecommendationPolicy(minimum_available_minutes=30),
    )
    assert below_threshold == ()


def test_quiet_hours_defer_noncritical_but_not_critical_recommendations() -> None:
    recommendations = generate_recommendations(
        now=at(10),
        signals=[
            RecommendationSignal(
                RecommendationSignalKind.QUIET_HOURS,
                "quiet:night",
                "Night quiet hours",
                start_at=at(10, 0),
                end_at=at(10, 23),
            ),
            RecommendationSignal(
                RecommendationSignalKind.DEADLINE,
                "task:soon",
                "Fictional deadline",
                due_at=at(11),
                priority_score=80,
            ),
            RecommendationSignal(
                RecommendationSignalKind.DEADLINE,
                "task:overdue",
                "Fictional overdue task",
                due_at=at(9),
            ),
        ],
    )
    by_code = {item.code: item for item in recommendations}

    assert by_code[RecommendationCode.QUIET_HOURS].delivery == RecommendationDelivery.READY
    assert (
        by_code[RecommendationCode.DEADLINE_APPROACHING].delivery
        == RecommendationDelivery.DEFERRED_QUIET_HOURS
    )
    assert by_code[RecommendationCode.OVERDUE].delivery == RecommendationDelivery.READY


def test_policy_can_disable_rules_and_filter_low_priority_deadlines() -> None:
    policy = RecommendationPolicy(
        enabled_codes=frozenset({RecommendationCode.DEADLINE_APPROACHING}),
        minimum_priority_score=50,
    )
    recommendations = generate_recommendations(
        now=at(10),
        policy=policy,
        signals=[
            RecommendationSignal(
                RecommendationSignalKind.DEADLINE,
                "task:low",
                "Low-priority fictional deadline",
                due_at=at(11),
                priority_score=40,
            ),
            RecommendationSignal(
                RecommendationSignalKind.DEADLINE,
                "task:high",
                "High-priority fictional deadline",
                due_at=at(11),
                priority_score=80,
            ),
            RecommendationSignal(
                RecommendationSignalKind.CONFLICT,
                "conflict:disabled",
                "Disabled fictional conflict",
                start_at=at(10, 13),
                end_at=at(10, 14),
            ),
        ],
    )

    assert [item.reference for item in recommendations] == ["task:high"]
