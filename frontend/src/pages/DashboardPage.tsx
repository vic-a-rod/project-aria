import { useMemo, useState } from "react";
import { AppHeader } from "../components/AppHeader";
import { MetricCard } from "../components/MetricCard";
import { StatusMessage } from "../components/StatusMessage";
import { TaskForm } from "../features/tasks/TaskForm";
import { TaskList } from "../features/tasks/TaskList";
import { useTasks } from "../features/tasks/useTasks";

export function DashboardPage() {
  const [filter, setFilter] = useState("All");
  const {
    tasks,
    loading,
    saving,
    updatingIds,
    error,
    retry,
    createTask,
    toggleCompleted,
  } = useTasks();

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
                <h2 id="responsibilities-title">Your responsibilities</h2>
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

            {error && <StatusMessage message={error} onRetry={tasks.length === 0 ? retry : undefined} />}
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
              <TaskList tasks={visibleTasks} updatingIds={updatingIds} onToggle={toggleCompleted} />
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
    </div>
  );
}

