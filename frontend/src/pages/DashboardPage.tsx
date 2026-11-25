import { useMemo, useRef, useState } from "react";
import { AppHeader } from "../components/AppHeader";
import { MetricCard } from "../components/MetricCard";
import { StatusMessage } from "../components/StatusMessage";
import { AssistantWorkspace } from "../features/assistant/AssistantWorkspace";
import { WeeklyAgenda } from "../features/agenda/WeeklyAgenda";
import { EventWorkspace } from "../features/events/EventWorkspace";
import type { CalendarEvent } from "../features/events/types";
import { TaskForm } from "../features/tasks/TaskForm";
import { DeleteTaskDialog } from "../features/tasks/DeleteTaskDialog";
import { TaskEditDialog } from "../features/tasks/TaskEditDialog";
import { TaskList } from "../features/tasks/TaskList";
import type { Task, TaskUpdate } from "../features/tasks/types";
import { useTasks } from "../features/tasks/useTasks";
import { TesterConsole } from "../features/tester/TesterConsole";

const testerConsoleEnabled = import.meta.env.VITE_ENABLE_TESTER_CONSOLE === "true";

export function DashboardPage() {
  const [categoryFilter, setCategoryFilter] = useState("All");
  const [completionFilter, setCompletionFilter] = useState<"all" | "open" | "completed">("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);
  const [eventState, setEventState] = useState<{
    events: CalendarEvent[];
    loading: boolean;
    error: string;
  }>({ events: [], loading: true, error: "" });
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const {
    tasks,
    loading,
    saving,
    updatingIds,
    deletingIds,
    error,
    notice,
    retry,
    createTask,
    toggleCompleted,
    updateTask,
    deleteTask,
    clearFeedback,
  } = useTasks();

  function rememberFocus() {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
  }

  function restoreTriggerFocus() {
    queueMicrotask(() => {
      if (returnFocusRef.current?.isConnected) returnFocusRef.current.focus();
    });
  }

  function openEditor(task: Task) {
    rememberFocus();
    clearFeedback();
    setEditingTask(task);
  }

  function closeEditor() {
    setEditingTask(null);
    restoreTriggerFocus();
  }

  async function saveTask(changes: TaskUpdate): Promise<boolean> {
    if (!editingTask) return false;
    const saved = await updateTask(editingTask.id, changes);
    if (saved) closeEditor();
    return saved;
  }

  function openDeleteConfirmation(task: Task) {
    rememberFocus();
    clearFeedback();
    setDeleteTarget(task);
  }

  function closeDeleteConfirmation() {
    setDeleteTarget(null);
    restoreTriggerFocus();
  }

  async function confirmDelete(): Promise<boolean> {
    if (!deleteTarget) return false;
    const deleted = await deleteTask(deleteTarget.id);
    if (deleted) {
      setDeleteTarget(null);
      queueMicrotask(() => document.getElementById("responsibilities-title")?.focus());
    }
    return deleted;
  }

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(tasks.map((task) => task.category)))],
    [tasks],
  );
  const normalizedQuery = searchQuery.trim().toLocaleLowerCase();
  const visibleTasks = tasks.filter((task) => {
    const matchesCategory = categoryFilter === "All" || task.category === categoryFilter;
    const matchesCompletion =
      completionFilter === "all" ||
      (completionFilter === "completed" ? task.is_completed : !task.is_completed);
    const searchableText = [
      task.title,
      task.description,
      task.category,
      task.project ?? "",
      ...task.tags,
    ]
      .join(" ")
      .toLocaleLowerCase();
    return matchesCategory && matchesCompletion && searchableText.includes(normalizedQuery);
  });
  const filtersActive =
    categoryFilter !== "All" || completionFilter !== "all" || normalizedQuery.length > 0;
  const openTasks = tasks.filter((task) => !task.is_completed);
  const focusMinutes = openTasks.reduce((sum, task) => sum + task.estimated_minutes, 0);
  const topPriority = openTasks.reduce(
    (highest, task) => Math.max(highest, task.priority.score),
    0,
  );

  return (
    <div className="app-shell">
      <AppHeader />

      <main id="main-content">
        <section className="hero" aria-labelledby="dashboard-title">
          <div>
            <p className="eyebrow">Today’s overview</p>
            <h1 id="dashboard-title">Make space for what matters.</h1>
            <p className="subtle">
              Aria ranks responsibilities with clear rules while leaving room for life.
            </p>
          </div>
          <div className="metrics" aria-label="Task overview">
            <MetricCard value={openTasks.length} label="open tasks" />
            <MetricCard
              value={`${Math.round((focusMinutes / 60) * 10) / 10}h`}
              label="estimated focus"
            />
            <MetricCard value={topPriority} label="top priority" />
          </div>
        </section>

        <div className="workspace">
          <section className="panel task-panel" aria-labelledby="responsibilities-title">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Prioritized queue</p>
                <h2 id="responsibilities-title" tabIndex={-1}>Your responsibilities</h2>
              </div>
              <div className="task-filters" aria-label="Task filters">
                <label className="search-control">
                  <span>Search tasks</span>
                  <input
                    type="search"
                    value={searchQuery}
                    placeholder="Search tasks"
                    onChange={(event) => setSearchQuery(event.target.value)}
                  />
                </label>
                <label className="filter-control">
                  <span>Category</span>
                  <select
                    value={categoryFilter}
                    onChange={(event) => setCategoryFilter(event.target.value)}
                  >
                    {categories.map((category) => (
                      <option key={category}>{category}</option>
                    ))}
                  </select>
                </label>
                <label className="filter-control">
                  <span>Status</span>
                  <select
                    value={completionFilter}
                    onChange={(event) =>
                      setCompletionFilter(event.target.value as "all" | "open" | "completed")
                    }
                  >
                    <option value="all">All statuses</option>
                    <option value="open">Open</option>
                    <option value="completed">Completed</option>
                  </select>
                </label>
              </div>
            </div>

            {!loading && tasks.length > 0 && (
              <p className="task-filter-summary" aria-live="polite">
                Showing {visibleTasks.length} of {tasks.length} tasks
              </p>
            )}

            {error && !editingTask && !deleteTarget && (
              <StatusMessage message={error} onRetry={tasks.length === 0 ? retry : undefined} />
            )}
            {notice && <StatusMessage message={notice} tone="success" />}
            {loading ? (
              <p className="empty" role="status">
                Loading your local tasks…
              </p>
            ) : visibleTasks.length === 0 ? (
              <div className="empty">
                <strong>
                  {filtersActive ? "No tasks match these filters." : "Your local workspace is ready."}
                </strong>
                <span>
                  {filtersActive
                    ? "Try a different search, category, or status."
                    : "Add a responsibility when you are ready—an empty schedule is valid too."}
                </span>
              </div>
            ) : (
              <TaskList
                tasks={visibleTasks}
                updatingIds={updatingIds}
                deletingIds={deletingIds}
                onToggle={toggleCompleted}
                onEdit={openEditor}
                onDelete={openDeleteConfirmation}
              />
            )}
          </section>

          <aside className="panel add-panel" aria-labelledby="add-task-title">
            <p className="eyebrow">Quick capture</p>
            <h2 id="add-task-title">Add a task</h2>
            <TaskForm saving={saving} onCreate={createTask} />
            <p className="privacy">
              Stored in this installation’s local database. No account, cloud sync, or AI
              service is required.
            </p>
          </aside>
        </div>

        <WeeklyAgenda
          tasks={tasks}
          events={eventState.events}
          loading={loading || eventState.loading}
          error={error || eventState.error}
        />

        <EventWorkspace onStateChange={setEventState} />

        <AssistantWorkspace onTaskCreated={retry} />

        {testerConsoleEnabled && <TesterConsole taskCount={tasks.length} />}
      </main>

      {editingTask && (
        <TaskEditDialog
          task={editingTask}
          saving={updatingIds.has(editingTask.id)}
          error={error}
          onCancel={closeEditor}
          onSave={saveTask}
        />
      )}
      {deleteTarget && (
        <DeleteTaskDialog
          task={deleteTarget}
          deleting={deletingIds.has(deleteTarget.id)}
          error={error}
          onCancel={closeDeleteConfirmation}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}

