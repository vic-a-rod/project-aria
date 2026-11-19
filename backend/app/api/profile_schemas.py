from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.profiles import NewProfile, Profile


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    def to_domain(self) -> NewProfile:
        return NewProfile(display_name=self.display_name)


class ProfileRead(BaseModel):
    id: str
    display_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_domain(cls, profile: Profile) -> "ProfileRead":
        return cls.model_validate(profile)
