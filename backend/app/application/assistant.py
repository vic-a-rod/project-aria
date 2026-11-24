import json
import re
from dataclasses import dataclass
from datetime import timedelta
from hashlib import sha256
from uuid import UUID, uuid4

from app.application.actions import ActionService
from app.application.authorization import AuthorizationContext
from app.application.clock import Clock
from app.application.command_results import (
    CommandResultPresenter,
    MutationPreview,
    ProposalEvidenceInput,
)
from app.application.contracts import (
    ActorContext,
    ClarificationRequest,
    CommandEnvelope,
    CommandResult,
    EvidenceReference,
    EvidenceSourceType,
    IntentKind,
    ProposedChange,
    ProposedMutationIntent,
    ReadIntent,
    ReasoningDetail,
    ResultStatus,
    SourceChannel,
)
from app.application.dispatcher import CommandDispatcher
from app.application.tasks import TaskService, TaskView
from app.domain.actions import ExecutionStatus
from app.domain.tasks import NewTask


class AssistantRequestError(ValueError):
    pass


class AssistantConfirmationError(ValueError):
    pass


@dataclass(frozen=True)
class AssistantRequest:
    text: str
    profile_id: str
    actor_id: str = "local-user"
    locale: str = "en-US"
    time_zone: str = "UTC"


@dataclass(frozen=True)
class AssistantConfirmation:
    proposal_id: UUID
    confirmation_id: UUID
    token: str
    profile_id: str
    actor_id: str = "local-user"


class LocalAssistantService:
    """Small offline command surface for the active local demo milestone."""

    _LIST_PATTERN = re.compile(
        r"^(?:show|list|view)(?:\s+me)?(?:\s+all)?\s+(?:my\s+)?tasks[.!?\s]*$",
        re.IGNORECASE,
    )
    _CREATE_PATTERN = re.compile(
        r"^(?:add|create)(?:\s+me)?\s+(?:a\s+)?task(?:\s*:\s*|\s+)(.*)$",
        re.IGNORECASE,
    )
    _INCOMPLETE_CREATE_PATTERN = re.compile(
        r"^(?:add|create)(?:\s+me)?\s+(?:a\s+)?task[.!?\s]*$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        tasks: TaskService,
        actions: ActionService,
        clock: Clock,
    ) -> None:
        self._tasks = tasks
        self._actions = actions
        self._clock = clock
        self._presenter = CommandResultPresenter(actions)

    def submit(self, request: AssistantRequest) -> CommandResult:
        text = " ".join(request.text.strip().split())
        if not text:
            raise AssistantRequestError("assistant request must not be blank")
        command = self._interpret(text, request)
        dispatcher = CommandDispatcher()
        dispatcher.register("tasks.list", IntentKind.READ, self._list_tasks)
        dispatcher.register("tasks.create", IntentKind.PROPOSED_MUTATION, self._create_task)
        return dispatcher.dispatch(
            command,
            AuthorizationContext.local(
                actor_id=request.actor_id,
                profile_id=request.profile_id,
            ),
        )

    def confirm(self, request: AssistantConfirmation) -> CommandResult:
        proposal = self._actions.get_proposal(str(request.proposal_id))
        if proposal.profile_id != request.profile_id:
            raise AssistantConfirmationError("proposal does not belong to the active profile")
        if proposal.action_type != "tasks.create":
            raise AssistantConfirmationError("unsupported assistant proposal")

        arguments = proposal.payload.get("arguments")
        if not isinstance(arguments, dict):
            raise AssistantConfirmationError("proposal arguments are invalid")
        state_hash = self._state_hash(arguments)
        self._actions.confirm(
            str(request.confirmation_id),
            token=request.token,
            current_state_hash=state_hash,
            actor_id=request.actor_id,
        )

        try:
            created = self._tasks.create(self._new_task(arguments))
        except (TypeError, ValueError) as error:
            self._actions.record_execution(
                proposal.id,
                str(request.confirmation_id),
                status=ExecutionStatus.FAILED,
                summary="The confirmed task could not be created.",
                error_code="invalid_task_arguments",
                actor_id=request.actor_id,
            )
            raise AssistantConfirmationError("confirmed task data is invalid") from error

        self._actions.record_execution(
            proposal.id,
            str(request.confirmation_id),
            status=ExecutionStatus.SUCCEEDED,
            summary=f'Task "{created.task.title}" was created locally.',
            error_code=None,
            actor_id=request.actor_id,
        )
        return CommandResult(
            command_name="tasks.create",
            correlation_id=uuid4(),
            status=ResultStatus.SUCCEEDED,
            data={"task": self._task_data(created)},
            evidence=(
                EvidenceReference(
                    source_type=EvidenceSourceType.LOCAL_TASK,
                    reference_id=str(created.task.id),
                    summary=f'Created local task "{created.task.title}".',
                    observed_at=self._clock.now(),
                ),
            ),
            reasoning=(
                ReasoningDetail(
                    code="confirmed_user_action",
                    summary="The saved task matches the explicitly confirmed preview.",
                ),
            ),
            display_summary=f'Created “{created.task.title}” in your local task list.',
            speakable_text=f'Created {created.task.title}.',
        )

    def _interpret(self, text: str, request: AssistantRequest) -> CommandEnvelope:
        actor = ActorContext(actor_id=request.actor_id, profile_id=request.profile_id)
        common = {
            "source_channel": SourceChannel.TEXT,
            "actor": actor,
            "correlation_id": uuid4(),
            "locale": request.locale,
            "time_zone": request.time_zone,
        }
        if self._LIST_PATTERN.fullmatch(text):
            return CommandEnvelope(
                intent=ReadIntent(name="tasks.list"),
                **common,
            )

        match = self._CREATE_PATTERN.fullmatch(text)
        if match:
            title = match.group(1).strip(" .")
            if len(title) > 200:
                raise AssistantRequestError("task titles cannot exceed 200 characters")
            return CommandEnvelope(
                intent=ProposedMutationIntent(
                    name="tasks.create",
                    arguments=self._task_arguments(title),
                    reason="The user asked Aria to create a local task.",
                ),
                idempotency_key=str(uuid4()),
                **common,
            )

        if self._INCOMPLETE_CREATE_PATTERN.fullmatch(text):
            return CommandEnvelope(
                intent=ProposedMutationIntent(
                    name="tasks.create",
                    arguments={},
                    reason="The user asked to create a task but did not provide a title.",
                ),
                idempotency_key=str(uuid4()),
                **common,
            )

        raise AssistantRequestError(
            'Try “show my tasks” or “add task: Review the fictional brief”.'
        )

    def _list_tasks(self, command: CommandEnvelope) -> CommandResult:
        views = self._tasks.list()
        evidence = tuple(
            EvidenceReference(
                source_type=EvidenceSourceType.LOCAL_TASK,
                reference_id=str(view.task.id),
                summary=f'Local task "{view.task.title}" has priority {view.priority.score:g}.',
                observed_at=self._clock.now(),
            )
            for view in views
        )
        count = len(views)
        summary = (
            "You do not have any tasks in this profile."
            if count == 0
            else f"Found {count} task{'s' if count != 1 else ''} in priority order."
        )
        return self._presenter.successful_read(
            command,
            data={"tasks": [self._task_data(view) for view in views]},
            evidence=evidence,
            reasoning=(
                ReasoningDetail(
                    code="deterministic_priority_sort",
                    summary="Tasks are ordered by Aria's deterministic priority score.",
                    details={"task_count": count},
                ),
            ),
            display_summary=summary,
            speakable_text=summary,
        )

    def _create_task(self, command: CommandEnvelope) -> CommandResult:
        arguments = dict(command.intent.arguments)
        title = str(arguments.get("title", "")).strip()
        if not title:
            return self._presenter.clarification(
                command,
                ClarificationRequest(
                    field="title",
                    question="What should the task be called?",
                    reason="A task title is required before Aria can prepare a preview.",
                ),
                reasoning=(
                    ReasoningDetail(
                        code="missing_required_field",
                        summary="No task title was included in the request.",
                    ),
                ),
                display_summary="I need a task title before I can prepare that change.",
                speakable_text="What should the task be called?",
            )

        now = self._clock.now()
        return self._presenter.proposed_mutation(
            command,
            MutationPreview(
                summary=f'Create a local task named "{title}".',
                changes=(ProposedChange(field="task", before=None, after=arguments),),
                evidence=(
                    ProposalEvidenceInput(
                        EvidenceReference(
                            source_type=EvidenceSourceType.USER_INPUT,
                            reference_id=str(command.correlation_id),
                            summary=f'The typed request asked to create "{title}".',
                            observed_at=now,
                        )
                    ),
                ),
                reasoning=(
                    ReasoningDetail(
                        code="explicit_task_creation_request",
                        summary="Aria mapped the explicit request to a task creation preview.",
                    ),
                ),
                warnings=(),
                state_hash=self._state_hash(arguments),
                proposal_expires_at=now + timedelta(minutes=15),
                confirmation_reason="Creating the task changes saved local data.",
                display_summary=f'Ready to create “{title}” with the shown defaults.',
                speakable_text=f'Ready to create {title}. Please confirm.',
            ),
        )

    def _state_hash(self, arguments: dict) -> str:
        task_state = [
            {"id": view.task.id, "updated_at": view.task.updated_at.isoformat()}
            for view in self._tasks.list()
        ]
        encoded = json.dumps(
            {"arguments": arguments, "tasks": task_state},
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(encoded.encode()).hexdigest()

    @staticmethod
    def _task_arguments(title: str) -> dict:
        return {
            "title": title,
            "description": "",
            "category": "Personal",
            "project": None,
            "tags": [],
            "start_date": None,
            "due_date": None,
            "estimated_minutes": 30,
            "importance": 3,
            "is_completed": False,
            "is_fixed": False,
            "recurrence": None,
            "recurrence_time_zone": None,
            "notes": "",
        }

    @staticmethod
    def _new_task(arguments: dict) -> NewTask:
        return NewTask(
            title=str(arguments["title"]),
            description=str(arguments.get("description", "")),
            category=str(arguments.get("category", "Personal")),
            project=arguments.get("project"),
            tags=tuple(arguments.get("tags", ())),
            start_date=None,
            due_date=None,
            estimated_minutes=int(arguments.get("estimated_minutes", 30)),
            importance=int(arguments.get("importance", 3)),
            is_completed=bool(arguments.get("is_completed", False)),
            is_fixed=bool(arguments.get("is_fixed", False)),
            recurrence=arguments.get("recurrence"),
            recurrence_time_zone=arguments.get("recurrence_time_zone"),
            notes=str(arguments.get("notes", "")),
        )

    @staticmethod
    def _task_data(view: TaskView) -> dict:
        task = view.task
        return {
            "id": task.id,
            "title": task.title,
            "category": task.category,
            "estimated_minutes": task.estimated_minutes,
            "importance": task.importance,
            "is_completed": task.is_completed,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "priority_score": view.priority.score,
            "priority_reasons": list(view.priority.reasons),
        }
