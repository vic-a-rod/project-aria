from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Profile:
    id: str
    display_name: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class NewProfile:
    display_name: str


def validate_profile(profile: Profile | NewProfile) -> None:
    if not profile.display_name.strip():
        raise ValueError("display_name must not be blank")
    if len(profile.display_name) > 100:
        raise ValueError("display_name cannot exceed 100 characters")
