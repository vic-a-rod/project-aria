from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.priority import (
    PriorityInput,
    PriorityWeights,
    ResponsibilityKind,
    calculate_priority,
    calculate_responsibility_priority,
)


def test_completed_task_has_zero_priority() -> None:
    result = calculate_priority(
        importance=5,
        due_date=date(2026, 11, 9),
        estimated_minutes=30,
        is_completed=True,
        today=date(2026, 11, 9),
    )
    assert result.score == 0
    assert result.reasons == ["Task is complete."]


def test_overdue_important_task_ranks_above_distant_task() -> None:
    today = date(2026, 11, 9)
    overdue = calculate_priority(
        importance=5,
        due_date=today - timedelta(days=1),
        estimated_minutes=60,
        is_completed=False,
        today=today,
    )
    distant = calculate_priority(
        importance=3,
        due_date=today + timedelta(days=60),
        estimated_minutes=60,
        is_completed=False,
        today=today,
    )
    assert overdue.score > distant.score
    assert any("Overdue" in reason for reason in overdue.reasons)


def test_short_task_receives_explained_quick_win_bonus() -> None:
    result = calculate_priority(
        importance=2,
        due_date=None,
        estimated_minutes=20,
        is_completed=False,
        today=date(2026, 11, 9),
    )
    assert result.score == 25
    assert any("quick-win" in reason for reason in result.reasons)


def test_all_responsibility_kinds_use_the_same_explainable_engine() -> None:
    now = datetime(2026, 11, 9, 17, 0, tzinfo=UTC)
    inputs = [
        PriorityInput(ResponsibilityKind.TASK, 3, now + timedelta(days=2), 30),
        PriorityInput(
            ResponsibilityKind.EVENT,
            3,
            now + timedelta(days=2),
            60,
            is_fixed=True,
        ),
        PriorityInput(ResponsibilityKind.DEADLINE, 5, now + timedelta(days=2), 0),
        PriorityInput(
            ResponsibilityKind.APPLICATION,
            4,
            now + timedelta(days=2),
            0,
            application_status="interviewing",
        ),
        PriorityInput(ResponsibilityKind.FOLLOW_UP, 4, now + timedelta(days=2), 15),
    ]

    results = [calculate_responsibility_priority(item, now=now) for item in inputs]

    assert all(result.score == sum(item.points for item in result.components) for result in results)
    assert "fixed_commitment" in results[1].reason_codes
    assert "application_interviewing" in results[3].reason_codes
    assert "quick_win" in results[4].reason_codes


def test_weights_are_configurable_and_score_cap_is_reconciled() -> None:
    now = datetime(2026, 11, 9, 17, 0, tzinfo=UTC)
    result = calculate_responsibility_priority(
        PriorityInput(
            ResponsibilityKind.APPLICATION,
            5,
            now - timedelta(days=2),
            15,
            is_fixed=True,
            application_status="offer",
        ),
        now=now,
        weights=PriorityWeights(importance_per_level=12, overdue=50),
    )

    assert result.score == 100
    assert result.reason_codes[-1] == "score_cap"
    assert result.score == sum(component.points for component in result.components)


def test_priority_requires_explicit_aware_time() -> None:
    responsibility = PriorityInput(
        ResponsibilityKind.EVENT,
        3,
        datetime(2026, 11, 10, 17, 0, tzinfo=UTC),
        60,
    )

    with pytest.raises(ValueError, match="now must be timezone-aware"):
        calculate_responsibility_priority(
            responsibility,
            now=datetime(2026, 11, 9, 17, 0),
        )

