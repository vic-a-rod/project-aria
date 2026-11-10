import type { Task } from "./types";

type TaskListProps = {
  tasks: Task[];
  updatingIds: Set<number>;
  deletingIds: Set<number>;
  onToggle: (task: Task) => void;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
};

export function TaskList({
  tasks,
  updatingIds,
  deletingIds,
  onToggle,
  onEdit,
  onDelete,
}: TaskListProps) {
  return (
    <ul className="task-list">
      {tasks.map((task) => {
        const updating = updatingIds.has(task.id);
        const deleting = deletingIds.has(task.id);
        const pending = updating || deleting;
        const action = task.is_completed ? "Reopen" : "Complete";

        return (
          <li key={task.id} className={task.is_completed ? "completed" : ""}>
            <button
              className="check"
              type="button"
              onClick={() => onToggle(task)}
              aria-label={`${action} ${task.title}`}
              aria-pressed={task.is_completed}
              disabled={pending}
            >
              {updating ? "…" : task.is_completed ? "✓" : ""}
            </button>
            <div className="task-copy">
              <strong>{task.title}</strong>
              <span>
                {task.category} · {task.estimated_minutes} min
                {task.due_date ? ` · due ${task.due_date}` : ""}
              </span>
              <details>
                <summary>Why this priority?</summary>
                {task.priority.reasons.map((reason) => (
                  <p key={reason}>{reason}</p>
                ))}
              </details>
            </div>
            <div className="score" aria-label={`Priority score ${task.priority.score}`}>
              <strong>{task.priority.score}</strong>
              <span>priority</span>
            </div>
            <div className="task-actions">
              <button
                className="text-button"
                type="button"
                onClick={() => onEdit(task)}
                aria-label={`Edit ${task.title}`}
                disabled={pending}
              >
                Edit
              </button>
              <button
                className="text-button danger-text"
                type="button"
                onClick={() => onDelete(task)}
                aria-label={`Delete ${task.title}`}
                disabled={pending}
              >
                Delete
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

