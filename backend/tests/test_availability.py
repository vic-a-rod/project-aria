from datetime import UTC, date, datetime, time

import pytest

from app.domain.availability import (
    AvailabilityBlock,
    AvailabilityBlockKind,
    ConflictKind,
    calculate_availability,
    recurring_wall_clock_blocks,
)


def instant(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 10, hour, minute, tzinfo=UTC)


def test_free_time_distinguishes_flexible_from_hard_constraints() -> None:
    result = calculate_availability(
        window_start=instant(8),
        window_end=instant(14),
        blocks=[
            AvailabilityBlock(
                "event:fixed",
                "Fictional appointment",
                instant(9),
                instant(10),
                AvailabilityBlockKind.FIXED,
            ),
            AvailabilityBlock(
                "task:flexible",
                "Fictional study block",
                instant(10),
                instant(11),
                AvailabilityBlockKind.FLEXIBLE,
            ),
            AvailabilityBlock(
                "preference:family",
                "Protected family time",
                instant(12),
                instant(13),
                AvailabilityBlockKind.PROTECTED,
            ),
        ],
    )

    assert [(item.start_at, item.end_at) for item in result.free_intervals] == [
        (instant(8), instant(9)),
        (instant(11), instant(12)),
        (instant(13), instant(14)),
    ]
    assert [(item.start_at, item.end_at) for item in result.hard_free_intervals] == [
        (instant(8), instant(9)),
        (instant(10), instant(12)),
        (instant(13), instant(14)),
    ]


def test_conflicts_are_stable_and_classify_flexible_overlap() -> None:
    result = calculate_availability(
        window_start=instant(8),
        window_end=instant(14),
        blocks=[
            AvailabilityBlock(
                "b-fixed", "Fixed B", instant(10), instant(12), AvailabilityBlockKind.FIXED
            ),
            AvailabilityBlock(
                "a-protected",
                "Protected A",
                instant(9),
                instant(11),
                AvailabilityBlockKind.PROTECTED,
            ),
            AvailabilityBlock(
                "c-flexible",
                "Flexible C",
                instant(10, 30),
                instant(13),
                AvailabilityBlockKind.FLEXIBLE,
            ),
        ],
    )

    assert [item.kind for item in result.conflicts] == [
        ConflictKind.HARD,
        ConflictKind.RESOLVABLE,
        ConflictKind.RESOLVABLE,
    ]
    assert result.conflicts[0].first_reference == "a-protected"
    assert result.conflicts[0].second_reference == "b-fixed"


def test_weekly_recurrence_preserves_local_time_across_dst() -> None:
    block = AvailabilityBlock(
        reference="event:weekly",
        title="Fictional weekly meeting",
        start_at=datetime.fromisoformat("2026-10-26T09:00:00-04:00"),
        end_at=datetime.fromisoformat("2026-10-26T10:00:00-04:00"),
        kind=AvailabilityBlockKind.FIXED,
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO;COUNT=3",
        recurrence_time_zone="America/New_York",
    )

    result = calculate_availability(
        window_start=datetime(2026, 10, 25, tzinfo=UTC),
        window_end=datetime(2026, 11, 10, tzinfo=UTC),
        blocks=[block],
    )

    assert [item.start_at for item in result.occurrences] == [
        datetime(2026, 10, 26, 13, 0, tzinfo=UTC),
        datetime(2026, 11, 2, 14, 0, tzinfo=UTC),
        datetime(2026, 11, 9, 14, 0, tzinfo=UTC),
    ]


def test_overnight_rest_adapter_and_invalid_recurrence() -> None:
    blocks = recurring_wall_clock_blocks(
        reference="preference:rest",
        title="Protected rest",
        kind=AvailabilityBlockKind.REST,
        days_of_week=(0, 1, 2, 3, 4, 5, 6),
        start_time=time(22),
        end_time=time(7),
        time_zone="UTC",
        anchor_date=date(2026, 11, 9),
    )
    result = calculate_availability(
        window_start=datetime(2026, 11, 9, 20, tzinfo=UTC),
        window_end=datetime(2026, 11, 10, 9, tzinfo=UTC),
        blocks=blocks,
    )
    assert [(item.start_at, item.end_at) for item in result.occurrences] == [
        (
            datetime(2026, 11, 9, 22, tzinfo=UTC),
            datetime(2026, 11, 10, 7, tzinfo=UTC),
        )
    ]

    invalid = AvailabilityBlock(
        "event:invalid",
        "Invalid recurrence",
        instant(9),
        instant(10),
        AvailabilityBlockKind.FIXED,
        recurrence_rule="FREQ=MONTHLY",
        recurrence_time_zone="UTC",
    )
    with pytest.raises(ValueError, match="supports FREQ=DAILY or FREQ=WEEKLY"):
        calculate_availability(
            window_start=instant(8), window_end=instant(14), blocks=[invalid]
        )
