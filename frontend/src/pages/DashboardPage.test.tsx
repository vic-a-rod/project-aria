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
    update: vi.fn(),
    remove: vi.fn(),
  },
}));

const fictionalTask: Task = {
  id: 41,
  title: "Review fictional course syllabus",
  description: "",
  category: "Education",
  project: null,
  tags: ["fictional"],
  start_date: null,
  due_date: "2030-01-15",
  estimated_minutes: 25,
  importance: 3,
  is_completed: false,
  completed_at: null,
  is_fixed: false,
  recurrence: null,
  recurrence_time_zone: null,
  notes: "",
  created_at: "2029-12-01T12:00:00Z",
  updated_at: "2029-12-01T12:00:00Z",
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

  it("edits every currently exposed task field and updates dashboard state", async () => {
    const user = userEvent.setup();
    const detailedTask: Task = {
      ...fictionalTask,
      description: "A fictional planning exercise.",
      project: "Project Aurora",
      start_date: "2030-01-10",
      recurrence: "FREQ=WEEKLY",
      recurrence_time_zone: "UTC",
      notes: "Use only invented course details.",
    };
    const updatedTask: Task = {
      ...detailedTask,
      title: "Draft fictional study outline",
      description: "Updated fictional planning exercise.",
      category: "Software projects",
      project: "Project Aria",
      tags: ["fictional", "planning"],
      start_date: "2030-01-11",
      due_date: "2030-01-20",
      estimated_minutes: 60,
      importance: 5,
      is_completed: true,
      is_fixed: true,
      recurrence: "FREQ=WEEKLY;BYDAY=MO",
      recurrence_time_zone: "America/Phoenix",
      notes: "Still contains no real user data.",
      priority: { score: 0, reasons: ["Task is complete."] },
    };
    mockedTaskApi.list.mockResolvedValue([detailedTask]);
    mockedTaskApi.update.mockResolvedValue(updatedTask);

    render(<DashboardPage />);
    await screen.findByText(detailedTask.title);

    await user.click(
      screen.getByRole("button", { name: `Edit ${detailedTask.title}` }),
    );

    const dialog = screen.getByRole("dialog", { name: "Edit task" });
    const editor = within(dialog);
    expect(editor.getByLabelText("Title")).toHaveFocus();
    expect(editor.getByLabelText("Description")).toHaveValue(detailedTask.description);
    expect(editor.getByLabelText("Project")).toHaveValue(detailedTask.project);
    expect(editor.getByLabelText("Start date")).toHaveValue(detailedTask.start_date);
    expect(editor.getByLabelText("Due date")).toHaveValue(detailedTask.due_date);
    expect(editor.getByLabelText("Recurrence rule")).toHaveValue(detailedTask.recurrence);
    expect(editor.getByLabelText("Recurrence time zone")).toHaveValue(
      detailedTask.recurrence_time_zone,
    );
    expect(editor.getByLabelText("Notes")).toHaveValue(detailedTask.notes);

    await user.clear(editor.getByLabelText("Title"));
    await user.type(editor.getByLabelText("Title"), updatedTask.title);
    await user.clear(editor.getByLabelText("Description"));
    await user.type(editor.getByLabelText("Description"), updatedTask.description);
    await user.clear(editor.getByLabelText("Category"));
    await user.type(editor.getByLabelText("Category"), updatedTask.category);
    await user.clear(editor.getByLabelText("Project"));
    await user.type(editor.getByLabelText("Project"), updatedTask.project!);
    await user.clear(editor.getByLabelText("Tags (comma separated)"));
    await user.type(editor.getByLabelText("Tags (comma separated)"), "fictional, planning");
    await user.clear(editor.getByLabelText("Start date"));
    await user.type(editor.getByLabelText("Start date"), updatedTask.start_date!);
    await user.clear(editor.getByLabelText("Due date"));
    await user.type(editor.getByLabelText("Due date"), updatedTask.due_date!);
    await user.clear(editor.getByLabelText("Estimated minutes"));
    await user.type(editor.getByLabelText("Estimated minutes"), "60");
    await user.selectOptions(editor.getByLabelText("Importance"), "5");
    await user.clear(editor.getByLabelText("Recurrence rule"));
    await user.type(editor.getByLabelText("Recurrence rule"), updatedTask.recurrence!);
    await user.clear(editor.getByLabelText("Recurrence time zone"));
    await user.type(
      editor.getByLabelText("Recurrence time zone"),
      updatedTask.recurrence_time_zone!,
    );
    await user.clear(editor.getByLabelText("Notes"));
    await user.type(editor.getByLabelText("Notes"), updatedTask.notes);
    await user.click(editor.getByLabelText("Fixed commitment"));
    await user.click(editor.getByLabelText("Completed"));
    await user.click(editor.getByRole("button", { name: "Save changes" }));

    await waitFor(() =>
      expect(mockedTaskApi.update).toHaveBeenCalledWith(
        detailedTask.id,
        expect.objectContaining({
          title: updatedTask.title,
          description: updatedTask.description,
          category: updatedTask.category,
          project: updatedTask.project,
          tags: updatedTask.tags,
          start_date: updatedTask.start_date,
          due_date: updatedTask.due_date,
          estimated_minutes: updatedTask.estimated_minutes,
          importance: updatedTask.importance,
          is_completed: updatedTask.is_completed,
          is_fixed: updatedTask.is_fixed,
          recurrence: updatedTask.recurrence,
          recurrence_time_zone: updatedTask.recurrence_time_zone,
          notes: updatedTask.notes,
        }),
      ),
    );
    expect(screen.queryByRole("dialog", { name: "Edit task" })).not.toBeInTheDocument();
    expect(await screen.findByText(updatedTask.title)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Task changes saved locally");
    expect(within(screen.getByLabelText("Task overview")).getByText("open tasks").closest("article"))
      .toHaveTextContent("0open tasks");
  }, 15_000);

  it("cancels editing with Escape and restores focus without saving", async () => {
    const user = userEvent.setup();
    mockedTaskApi.list.mockResolvedValue([fictionalTask]);

    render(<DashboardPage />);
    await screen.findByText(fictionalTask.title);
    const editButton = screen.getByRole("button", { name: `Edit ${fictionalTask.title}` });

    await user.click(editButton);
    const title = within(screen.getByRole("dialog")).getByLabelText("Title");
    await user.clear(title);
    await user.type(title, "Unsaved fictional title");
    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(mockedTaskApi.update).not.toHaveBeenCalled();
    expect(screen.getByText(fictionalTask.title)).toBeInTheDocument();
    await waitFor(() => expect(editButton).toHaveFocus());
  });

  it("requires deletion confirmation, supports cancel, and deletes after confirmation", async () => {
    const user = userEvent.setup();
    mockedTaskApi.list.mockResolvedValue([fictionalTask]);
    mockedTaskApi.remove.mockResolvedValue(undefined);

    render(<DashboardPage />);
    await screen.findByText(fictionalTask.title);
    const deleteButton = screen.getByRole("button", {
      name: `Delete ${fictionalTask.title}`,
    });

    await user.click(deleteButton);
    const firstConfirmation = screen.getByRole("alertdialog");
    expect(within(firstConfirmation).getByRole("button", { name: "Keep task" })).toHaveFocus();
    await user.click(within(firstConfirmation).getByRole("button", { name: "Keep task" }));

    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(mockedTaskApi.remove).not.toHaveBeenCalled();
    expect(screen.getByText(fictionalTask.title)).toBeInTheDocument();
    await waitFor(() => expect(deleteButton).toHaveFocus());

    await user.click(deleteButton);
    await user.click(
      within(screen.getByRole("alertdialog")).getByRole("button", { name: "Delete task" }),
    );

    await waitFor(() => expect(mockedTaskApi.remove).toHaveBeenCalledWith(fictionalTask.id));
    expect(screen.queryByText(fictionalTask.title)).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Task deleted");
    expect(screen.getByText("Your responsibilities")).toHaveFocus();
  });

  it("keeps dialogs open and reports edit and delete API failures", async () => {
    const user = userEvent.setup();
    mockedTaskApi.list.mockResolvedValue([fictionalTask]);
    mockedTaskApi.update.mockRejectedValue(new Error("Aria API returned 500"));
    mockedTaskApi.remove.mockRejectedValue(new Error("Aria API returned 503"));

    render(<DashboardPage />);
    await screen.findByText(fictionalTask.title);

    await user.click(screen.getByRole("button", { name: `Edit ${fictionalTask.title}` }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Save changes" }));

    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent(
      "could not save those changes",
    );
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Cancel" }));

    await user.click(screen.getByRole("button", { name: `Delete ${fictionalTask.title}` }));
    const confirmation = screen.getByRole("alertdialog");
    await user.click(within(confirmation).getByRole("button", { name: "Delete task" }));

    expect(await within(confirmation).findByRole("alert")).toHaveTextContent(
      "could not delete that task",
    );
    expect(screen.getByText(fictionalTask.title)).toBeInTheDocument();
  });
});

