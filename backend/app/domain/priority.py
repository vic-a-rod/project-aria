from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PriorityResult:
    score: float
    reasons: list[str]


def calculate_priority(
    *,
    importance: int,
    due_date: date | None,
    estimated_minutes: int,
    is_completed: bool,
    today: date | None = None,
) -> PriorityResult:
    """Return a deterministic 0-100 priority score and its explanation."""
    if is_completed:
        return PriorityResult(score=0.0, reasons=["Task is complete."])

    current_day = today or date.today()
    score = importance * 10.0
    reasons = [f"Importance {importance}/5 contributes {importance * 10} points."]

    if due_date is None:
        reasons.append("No deadline pressure was added.")
    else:
        days_remaining = (due_date - current_day).days
        if days_remaining < 0:
            urgency = 45.0
            reasons.append(f"Overdue by {abs(days_remaining)} day(s) adds 45 points.")
        elif days_remaining == 0:
            urgency = 40.0
            reasons.append("Due today adds 40 points.")
        elif days_remaining <= 2:
            urgency = 32.0
            reasons.append(f"Due in {days_remaining} day(s) adds 32 points.")
        elif days_remaining <= 7:
            urgency = 22.0
            reasons.append(f"Due within a week adds 22 points ({days_remaining} days remain).")
        elif days_remaining <= 30:
            urgency = 12.0
            reasons.append(f"Due within a month adds 12 points ({days_remaining} days remain).")
        else:
            urgency = 4.0
            reasons.append(f"Long-range deadline adds 4 points ({days_remaining} days remain).")
        score += urgency

    if estimated_minutes <= 30:
        score += 5.0
        reasons.append("A short task adds 5 quick-win points.")
    elif estimated_minutes > 240:
        score -= 5.0
        reasons.append("A large task subtracts 5 points until it can be broken down or scheduled.")

    return PriorityResult(score=round(max(0.0, min(score, 100.0)), 1), reasons=reasons)

