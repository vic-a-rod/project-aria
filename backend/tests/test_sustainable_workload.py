from datetime import UTC, datetime

from app.domain.availability import AvailabilityInterval
from app.domain.scheduling import ScheduleItem
from app.domain.sustainable_workload import (
    DeferralReason,
    SustainableMode,
    WorkloadModeState,
    WorkloadPolicy,
    WorkloadWarningCode,
    plan_sustainable_workload,
)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 10, hour, minute, tzinfo=UTC)


def test_focus_mode_defers_only_safe_out_of_scope_work() -> None:
    plan = plan_sustainable_workload(
        items=[
            ScheduleItem("task:focus", "Focused fictional work", 60, 80, None),
            ScheduleItem("task:deadline", "Protected deadline", 60, 60, at(14)),
            ScheduleItem("task:later", "Safe later work", 60, 70, None),
        ],
        hard_free_intervals=[AvailabilityInterval(at(9), at(17))],
        now=at(8),
        time_zone="UTC",
        mode_state=WorkloadModeState(
            SustainableMode.FOCUS,
            expires_at=at(18),
            focus_references=("task:focus",),
        ),
    )

    assert plan.effective_mode == SustainableMode.FOCUS
    assert {item.reference for item in plan.schedule.placements} == {
        "task:focus",
        "task:deadline",
    }
    assert [(item.reference, item.reason) for item in plan.deferrals] == [
        ("task:later", DeferralReason.FOCUS_SCOPE)
    ]


def test_lighter_mode_caps_work_and_reports_overload_without_erasing_deadlines() -> None:
    plan = plan_sustainable_workload(
        items=[
            ScheduleItem("task:one", "Fictional deadline one", 120, 80, at(15)),
            ScheduleItem("task:two", "Fictional deadline two", 120, 70, at(16)),
        ],
        hard_free_intervals=[AvailabilityInterval(at(9), at(17))],
        now=at(8),
        time_zone="UTC",
        mode_state=WorkloadModeState(SustainableMode.LIGHTER, expires_at=at(18)),
        policy=WorkloadPolicy(
            normal_daily_capacity_minutes=360,
            lighter_daily_capacity_minutes=180,
            reserve_unscheduled_minutes=60,
        ),
    )

    assert plan.daily_workload[0].capacity_minutes == 180
    assert plan.daily_workload[0].unscheduled_minutes == 360
    assert plan.schedule.scheduled_minutes == 120
    assert len(plan.schedule.unscheduled_references) == 1
    assert {item.code for item in plan.warnings} == {
        WorkloadWarningCode.OVERLOAD,
        WorkloadWarningCode.DEADLINE_AT_RISK,
    }
    assert any(item.reason == DeferralReason.CAPACITY for item in plan.deferrals)


def test_protected_family_time_is_never_scheduled_and_rest_is_legitimate() -> None:
    plan = plan_sustainable_workload(
        items=[ScheduleItem("task:family", "Fictional work", 180, 70, None)],
        hard_free_intervals=[AvailabilityInterval(at(9), at(17))],
        protected_intervals=[AvailabilityInterval(at(12), at(14))],
        now=at(8),
        time_zone="UTC",
        policy=WorkloadPolicy(
            normal_daily_capacity_minutes=360,
            lighter_daily_capacity_minutes=180,
            reserve_unscheduled_minutes=60,
        ),
    )

    placement = plan.schedule.placements[0]
    assert (placement.start_at, placement.end_at) == (at(9), at(12))
    assert plan.daily_workload[0].capacity_minutes == 300
    assert plan.daily_workload[0].unscheduled_minutes == 180


def test_expired_mode_returns_to_normal_capacity() -> None:
    plan = plan_sustainable_workload(
        items=[ScheduleItem("task:normal", "Fictional work", 240, 50, None)],
        hard_free_intervals=[AvailabilityInterval(at(9), at(17))],
        now=at(8),
        time_zone="UTC",
        mode_state=WorkloadModeState(SustainableMode.LIGHTER, expires_at=at(7)),
    )

    assert plan.effective_mode == SustainableMode.NORMAL
    assert plan.daily_workload[0].capacity_minutes == 360
    assert plan.schedule.scheduled_minutes == 240


def test_focus_mode_preserves_deadline_even_when_protected_time_fills_window() -> None:
    plan = plan_sustainable_workload(
        items=[
            ScheduleItem("task:deadline", "Fictional deadline", 60, 80, at(14)),
            ScheduleItem("task:later", "Fictional later work", 60, 70, None),
        ],
        hard_free_intervals=[AvailabilityInterval(at(9), at(17))],
        protected_intervals=[AvailabilityInterval(at(9), at(17))],
        now=at(8),
        time_zone="UTC",
        mode_state=WorkloadModeState(
            SustainableMode.FOCUS,
            expires_at=at(18),
            focus_references=("task:other",),
        ),
    )

    assert plan.schedule.unscheduled_references == ("task:deadline",)
    assert [(item.reference, item.reason) for item in plan.deferrals] == [
        ("task:deadline", DeferralReason.CAPACITY),
        ("task:later", DeferralReason.FOCUS_SCOPE),
    ]
    assert {warning.code for warning in plan.warnings} == {
        WorkloadWarningCode.OVERLOAD,
        WorkloadWarningCode.DEADLINE_AT_RISK,
    }
