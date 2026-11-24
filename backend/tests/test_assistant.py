from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from app.application.actions import ActionService, ActionStateError
from app.application.assistant import (
    AssistantConfirmation,
    AssistantRequest,
    AssistantRequestError,
    LocalAssistantService,
)
from app.application.contracts import ResultStatus
from app.application.tasks import TaskService
from app.domain.tasks import NewTask
from app.infrastructure.action_repository import SqlAlchemyActionRepository
from app.infrastructure.database import create_database_engine, create_session_factory
from app.infrastructure.migrations_runner import upgrade_database
from app.infrastructure.task_repository import SqlAlchemyTaskRepository

NOW = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)


@dataclass(frozen=True)
class FixedClock:
    instant: datetime = NOW

    def now(self) -> datetime:
        return self.instant

    def today(self) -> date:
        return self.instant.date()


def task(title: str) -> NewTask:
    return NewTask(
        title=title,
        description="",
        category="Personal",
        project=None,
        tags=(),
        start_date=None,
        due_date=None,
        estimated_minutes=30,
        importance=3,
        is_completed=False,
        is_fixed=False,
        recurrence=None,
        recurrence_time_zone=None,
        notes="",
    )


def service_for(session) -> LocalAssistantService:
    clock = FixedClock()
    return LocalAssistantService(
        TaskService(SqlAlchemyTaskRepository(session, "local-default"), clock),
        ActionService(SqlAlchemyActionRepository(session), clock),
        clock,
    )


def test_lists_profile_tasks_with_evidence_and_reasoning(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'assistant-read.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            repository = SqlAlchemyTaskRepository(session, "local-default")
            repository.create(task("Review fictional launch notes"), timestamp=NOW)

            result = service_for(session).submit(
                AssistantRequest(text="show my tasks", profile_id="local-default")
            )

            assert result.status == ResultStatus.SUCCEEDED
            assert result.data["tasks"][0]["title"] == "Review fictional launch notes"
            assert result.evidence[0].source_type.value == "local_task"
            assert result.reasoning[0].code == "deterministic_priority_sort"
    finally:
        engine.dispose()


def test_create_requires_title_then_returns_non_mutating_preview(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'assistant-preview.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            service = service_for(session)
            clarification = service.submit(
                AssistantRequest(text="add a task", profile_id="local-default")
            )
            assert clarification.status == ResultStatus.NEEDS_CLARIFICATION
            assert clarification.clarification is not None
            assert clarification.clarification.field == "title"

            preview = service.submit(
                AssistantRequest(
                    text="add task: Draft fictional demo script",
                    profile_id="local-default",
                )
            )
            assert preview.status == ResultStatus.REQUIRES_CONFIRMATION
            assert preview.confirmation is not None
            assert preview.proposals[0].changes[0].after["title"] == (
                "Draft fictional demo script"
            )
            assert SqlAlchemyTaskRepository(session, "local-default").list() == []
    finally:
        engine.dispose()


def test_confirmation_rechecks_state_and_creates_task_once(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'assistant-confirm.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            service = service_for(session)
            preview = service.submit(
                AssistantRequest(
                    text="create a task Prepare fictional dashboard tour",
                    profile_id="local-default",
                )
            )
            assert preview.confirmation is not None
            proposal = preview.proposals[0]
            confirmation = preview.confirmation

            result = service.confirm(
                AssistantConfirmation(
                    proposal_id=proposal.proposal_id,
                    confirmation_id=confirmation.confirmation_id,
                    token=confirmation.token,
                    profile_id="local-default",
                )
            )

            assert result.status == ResultStatus.SUCCEEDED
            assert result.data["task"]["title"] == "Prepare fictional dashboard tour"
            assert [item.title for item in SqlAlchemyTaskRepository(
                session, "local-default"
            ).list()] == ["Prepare fictional dashboard tour"]

            with pytest.raises(ActionStateError, match="already been used"):
                service.confirm(
                    AssistantConfirmation(
                        proposal_id=proposal.proposal_id,
                        confirmation_id=confirmation.confirmation_id,
                        token=confirmation.token,
                        profile_id="local-default",
                    )
                )
    finally:
        engine.dispose()


def test_unknown_request_fails_with_supported_examples(tmp_path) -> None:
    engine = create_database_engine(
        f"sqlite:///{(tmp_path / 'assistant-unknown.db').as_posix()}"
    )
    upgrade_database(engine)
    sessions = create_session_factory(engine)
    try:
        with sessions() as session:
            with pytest.raises(AssistantRequestError, match="show my tasks"):
                service_for(session).submit(
                    AssistantRequest(
                        text="do something unspecified",
                        profile_id="local-default",
                    )
                )
    finally:
        engine.dispose()
