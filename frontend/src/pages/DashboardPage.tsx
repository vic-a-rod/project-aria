import { useMemo, useRef, useState } from "react";
import { AppHeader } from "../components/AppHeader";
import { MetricCard } from "../components/MetricCard";
import { StatusMessage } from "../components/StatusMessage";
import { TaskForm } from "../features/tasks/TaskForm";
import { DeleteTaskDialog } from "../features/tasks/DeleteTaskDialog";
import { TaskEditDialog } from "../features/tasks/TaskEditDialog";
import { TaskList } from "../features/tasks/TaskList";
import type { Task, TaskUpdate } from "../features/tasks/types";
import { useTasks } from "../features/tasks/useTasks";

export function DashboardPage() {
  const [filter, setFilter] = useState("All");
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);
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
  const visibleTasks = tasks.filter(
    (task) => filter === "All" || task.category === filter,
  );
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
              <label className="filter-control">
                <span>Category</span>
                <select value={filter} onChange={(event) => setFilter(event.target.value)}>
                  {categories.map((category) => (
                    <option key={category}>{category}</option>
                  ))}
                </select>
              </label>
            </div>

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
                <strong>{filter === "All" ? "Your local workspace is ready." : `No ${filter} tasks.`}</strong>
                <span>
                  {filter === "All"
                    ? "Add a responsibility when you are ready—an empty schedule is valid too."
                    : "Choose another category or add a task for this one."}
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

