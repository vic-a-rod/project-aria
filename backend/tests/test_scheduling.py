from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.domain.availability import (
    AvailabilityConflict,
    AvailabilityInterval,
    ConflictKind,
)
from app.domain.scheduling import (
    ScheduleChangeKind,
    ScheduleItem,
    ScheduleRiskCode,
    ScheduleSource,
    ScheduleStrategy,
    simulate_schedules,
)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 10, hour, minute, tzinfo=UTC)


def test_simulation_returns_distinct_alternatives_and_structured_diffs() -> None:
    items = [
        ScheduleItem(
            reference="task:priority",
            title="High-priority fictional work",
            duration_minutes=120,
            priority_score=90,
            due_at=at(17),
            current_start_at=at(13),
            current_end_at=at(15),
        ),
        ScheduleItem(
            reference="task:deadline",
            title="Fictional near-deadline work",
            duration_minutes=60,
            priority_score=60,
            due_at=at(10, 30),
        ),
    ]
    original = deepcopy(items)

    priority_first, deadline_first = simulate_schedules(
        items=items,
        hard_free_intervals=[AvailabilityInterval(at(9), at(12))],
        now=at(8),
    )

    assert priority_first.strategy == ScheduleStrategy.PRIORITY_FIRST
    assert priority_first.unscheduled_references == ("task:deadline",)
    assert {risk.code for risk in priority_first.risks} == {
        ScheduleRiskCode.DEADLINE
    }
    assert deadline_first.unscheduled_references == ()
    assert [item.reference for item in deadline_first.placements] == [
        "task:deadline",
        "task:priority",
    ]
    change = next(
        item for item in deadline_first.changes if item.reference == "task:priority"
    )
    assert change.kind == ScheduleChangeKind.MOVED
    assert change.before_start_at == at(13)
    assert change.after_start_at == at(10)
    assert items == original


def test_fixed_and_external_commitments_never_move() -> None:
    items = [
        ScheduleItem(
            "event:fixed",
            "Fictional fixed appointment",
            60,
            80,
            at(12),
            is_fixed=True,
            current_start_at=at(9),
            current_end_at=at(10),
        ),
        ScheduleItem(
            "event:external",
            "Fictional external calendar event",
            60,
            70,
            at(12),
            source=ScheduleSource.EXTERNAL,
            current_start_at=at(9, 30),
            current_end_at=at(10, 30),
        ),
    ]
    conflict = AvailabilityConflict(
        ConflictKind.HARD,
        "event:fixed",
        "event:external",
        at(9, 30),
        at(10),
    )

    proposal = simulate_schedules(
        items=items,
        hard_free_intervals=[AvailabilityInterval(at(10, 30), at(12))],
        hard_conflicts=[conflict],
        now=at(8),
        strategies=(ScheduleStrategy.PRIORITY_FIRST,),
    )[0]

    assert [(item.reference, item.start_at) for item in proposal.placements] == [
        ("event:fixed", at(9)),
        ("event:external", at(9, 30)),
    ]
    assert all(item.kind == ScheduleChangeKind.UNCHANGED for item in proposal.changes)
    assert proposal.risks[0].code == ScheduleRiskCode.LOCKED_CONFLICT


def test_unscheduled_capacity_risk_and_locked_item_without_placement() -> None:
    proposal = simulate_schedules(
        items=[
            ScheduleItem("task:large", "Large fictional task", 180, 50, None),
            ScheduleItem(
                "event:locked",
                "Unplaced locked commitment",
                60,
                50,
                None,
                is_fixed=True,
            ),
        ],
        hard_free_intervals=[AvailabilityInterval(at(9), at(10))],
        now=at(8),
        strategies=(ScheduleStrategy.PRIORITY_FIRST,),
    )[0]

    assert proposal.unscheduled_references == ("task:large",)
    assert {risk.code for risk in proposal.risks} == {
        ScheduleRiskCode.CAPACITY
    }
    assert {
        item.kind for item in proposal.changes
    } == {ScheduleChangeKind.UNSCHEDULED}


def test_simulation_rejects_naive_time_and_overlapping_free_intervals() -> None:
    with pytest.raises(ValueError, match="now must be timezone-aware"):
        simulate_schedules(items=[], hard_free_intervals=[], now=datetime(2026, 11, 10))

    with pytest.raises(ValueError, match="must not overlap"):
        simulate_schedules(
            items=[],
            hard_free_intervals=[
                AvailabilityInterval(at(9), at(11)),
                AvailabilityInterval(at(10), at(12)),
            ],
            now=at(8),
        )
