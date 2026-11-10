import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { taskApi } from "../features/tasks/api";
import type { Task } from "../features/tasks/types";
import { DashboardPage } from "./DashboardPage";

vi.mock("../features/tasks/api", () => ({
  taskApi: {
    list: vi.fn(),
    create: vi.fn(),
    setCompleted: vi.fn(),
  },
}));

const fictionalTask: Task = {
  id: 41,
  title: "Review fictional course syllabus",
  description: "",
  category: "Education",
  tags: ["fictional"],
  start_date: null,
  due_date: "2030-01-15",
  estimated_minutes: 25,
  importance: 3,
  is_completed: false,
  is_fixed: false,
  recurrence: null,
  notes: "",
  priority: {
    score: 35,
    reasons: ["Importance 3/5 contributes 30 points.", "A short task adds 5 quick-win points."],
  },
};

const mockedTaskApi = vi.mocked(taskApi);

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((settle) => {
    resolve = settle;
  });
  return { promise, resolve };
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading and then an empty local workspace", async () => {
    const request = deferred<Task[]>();
    mockedTaskApi.list.mockReturnValue(request.promise);

    render(<DashboardPage />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading your local tasks");
    request.resolve([]);

    expect(await screen.findByText("Your local workspace is ready.")).toBeInTheDocument();
    expect(screen.getByText(/empty schedule is valid/i)).toBeInTheDocument();
    expect(screen.getByText(/no account, cloud sync, or AI service is required/i)).toBeInTheDocument();
  });

  it("shows an API failure and retries the local load", async () => {
    const user = userEvent.setup();
    mockedTaskApi.list
      .mockRejectedValueOnce(new Error("Aria API returned 503"))
      .mockResolvedValueOnce([]);

    render(<DashboardPage />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("The local API is unavailable");

    await user.click(within(alert).getByRole("button", { name: "Try again" }));

    await waitFor(() => expect(mockedTaskApi.list).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Your local workspace is ready.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("creates a fictional task through the quick-capture form", async () => {
    const user = userEvent.setup();
    mockedTaskApi.list.mockResolvedValue([]);
    mockedTaskApi.create.mockResolvedValue(fictionalTask);

    render(<DashboardPage />);
    await screen.findByText("Your local workspace is ready.");

    const titleInput = screen.getByLabelText("What needs doing?");
    const form = titleInput.closest("form");
    expect(form).not.toBeNull();
    const quickCapture = within(form!);

    await user.type(titleInput, `  ${fictionalTask.title}  `);
    await user.selectOptions(quickCapture.getByLabelText("Category"), fictionalTask.category);
    await user.clear(quickCapture.getByLabelText("Minutes"));
    await user.type(
      quickCapture.getByLabelText("Minutes"),
      String(fictionalTask.estimated_minutes),
    );
    await user.click(quickCapture.getByRole("button", { name: "Add to Aria" }));

    await waitFor(() =>
      expect(mockedTaskApi.create).toHaveBeenCalledWith(
        expect.objectContaining({
          title: fictionalTask.title,
          category: fictionalTask.category,
          estimated_minutes: fictionalTask.estimated_minutes,
        }),
      ),
    );
    expect(await screen.findByText(fictionalTask.title)).toBeInTheDocument();
    expect(screen.getByLabelText(`Priority score ${fictionalTask.priority.score}`)).toBeInTheDocument();
    expect(screen.getByLabelText("What needs doing?")).toHaveValue("");
  });

  it("completes and reopens a task while preserving its presentation", async () => {
    const user = userEvent.setup();
    const completedTask: Task = {
      ...fictionalTask,
      is_completed: true,
      priority: { score: 0, reasons: ["Task is complete."] },
    };
    mockedTaskApi.list.mockResolvedValue([fictionalTask]);
    mockedTaskApi.setCompleted
      .mockResolvedValueOnce(completedTask)
      .mockResolvedValueOnce(fictionalTask);

    render(<DashboardPage />);

    const taskTitle = await screen.findByText(fictionalTask.title);
    const taskRow = taskTitle.closest("li");
    expect(taskRow).not.toBeNull();
    expect(taskRow).toHaveTextContent(`${fictionalTask.category} · 25 min`);
    expect(within(taskRow!).getByText("Why this priority?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: `Complete ${fictionalTask.title}` }));

    await waitFor(() =>
      expect(mockedTaskApi.setCompleted).toHaveBeenLastCalledWith(fictionalTask.id, true),
    );
    const reopen = await screen.findByRole("button", { name: `Reopen ${fictionalTask.title}` });
    expect(reopen).toHaveAttribute("aria-pressed", "true");

    await user.click(reopen);

    await waitFor(() =>
      expect(mockedTaskApi.setCompleted).toHaveBeenLastCalledWith(fictionalTask.id, false),
    );
    expect(
      await screen.findByRole("button", { name: `Complete ${fictionalTask.title}` }),
    ).toHaveAttribute("aria-pressed", "false");
  });
});

