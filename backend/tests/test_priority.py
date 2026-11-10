from datetime import date, timedelta

from app.domain.priority import calculate_priority


def test_completed_task_has_zero_priority() -> None:
    result = calculate_priority(
        importance=5, due_date=date.today(), estimated_minutes=30, is_completed=True
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
        importance=2, due_date=None, estimated_minutes=20, is_completed=False
    )
    assert result.score == 25
    assert any("quick-win" in reason for reason in result.reasons)

