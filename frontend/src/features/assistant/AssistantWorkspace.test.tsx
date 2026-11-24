import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { assistantApi } from "./api";
import { AssistantWorkspace } from "./AssistantWorkspace";
import type { AssistantResult } from "./types";

vi.mock("./api", () => ({
  assistantApi: {
    send: vi.fn(),
    confirm: vi.fn(),
  },
}));

const preview: AssistantResult = {
  command_name: "tasks.create",
  correlation_id: "11111111-1111-4111-8111-111111111111",
  status: "requires_confirmation",
  data: {},
  warnings: [],
  evidence: [
    {
      source_type: "user_input",
      reference_id: "request:fictional",
      summary: "The typed request asked to create a fictional task.",
      observed_at: "2026-11-24T09:00:00Z",
    },
  ],
  reasoning: [
    {
      code: "explicit_task_creation_request",
      summary: "The explicit request maps to a task creation preview.",
      details: {},
    },
  ],
  proposals: [
    {
      proposal_id: "22222222-2222-4222-8222-222222222222",
      action: "tasks.create",
      summary: "Create a fictional demo task.",
      changes: [
        {
          field: "task",
          before: null,
          after: { title: "Review fictional brief", estimated_minutes: 30 },
        },
      ],
    },
  ],
  clarification: null,
  confirmation: {
    confirmation_id: "33333333-3333-4333-8333-333333333333",
    proposal_id: "22222222-2222-4222-8222-222222222222",
    token: "fictional-confirmation-token",
    expires_at: "2026-11-24T09:10:00Z",
    reason: "Creating the task changes saved local data.",
  },
  display_summary: "Ready to create the fictional task.",
  speakable_text: "Ready to create the task.",
};

const completed: AssistantResult = {
  ...preview,
  status: "succeeded",
  data: { task: { id: 7, title: "Review fictional brief" } },
  proposals: [],
  confirmation: null,
  display_summary: "Created “Review fictional brief” in your local task list.",
  speakable_text: "Created Review fictional brief.",
};

const mockedApi = vi.mocked(assistantApi);

describe("AssistantWorkspace", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows a mutation preview and executes only after confirmation", async () => {
    const user = userEvent.setup();
    const onTaskCreated = vi.fn();
    mockedApi.send.mockResolvedValue(preview);
    mockedApi.confirm.mockResolvedValue(completed);

    render(<AssistantWorkspace onTaskCreated={onTaskCreated} />);
    await user.type(screen.getByLabelText("Ask Aria"), "add task: Review fictional brief");
    await user.click(screen.getByRole("button", { name: "Send request" }));

    expect(mockedApi.send).toHaveBeenCalledWith("add task: Review fictional brief");
    const proposal = await screen.findByText("Proposed change");
    const result = proposal.closest<HTMLElement>(".assistant-result");
    expect(result).not.toBeNull();
    expect(within(result!).getByText(/changes saved local data/i)).toBeInTheDocument();
    expect(onTaskCreated).not.toHaveBeenCalled();

    await user.click(within(result!).getByRole("button", { name: "Confirm and save" }));

    await waitFor(() => expect(mockedApi.confirm).toHaveBeenCalledWith(preview.confirmation));
    expect(await screen.findByText(/Created “Review fictional brief”/)).toBeInTheDocument();
    expect(onTaskCreated).toHaveBeenCalledOnce();
  });

  it("renders clarification without a confirmation action", async () => {
    const user = userEvent.setup();
    mockedApi.send.mockResolvedValue({
      ...preview,
      status: "needs_clarification",
      proposals: [],
      confirmation: null,
      clarification: {
        field: "title",
        question: "What should the task be called?",
        reason: "A task title is required.",
        allow_free_text: true,
      },
      display_summary: "I need a task title before I can prepare that change.",
    });

    render(<AssistantWorkspace onTaskCreated={vi.fn()} />);
    await user.type(screen.getByLabelText("Ask Aria"), "add a task{Enter}");

    expect(await screen.findByText("What should the task be called?")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm and save" })).not.toBeInTheDocument();
    expect(mockedApi.confirm).not.toHaveBeenCalled();
  });
});
