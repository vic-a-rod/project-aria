import { FormEvent, useEffect, useRef, useState } from "react";
import { handleDialogKeyboard } from "../../components/dialogKeyboard";
import type { Task, TaskUpdate } from "./types";

type TaskEditDialogProps = {
  task: Task;
  saving: boolean;
  error?: string;
  onCancel: () => void;
  onSave: (changes: TaskUpdate) => Promise<boolean>;
};

type EditDraft = Omit<TaskUpdate, "tags"> & { tags: string };

function createDraft(task: Task): EditDraft {
  return {
    title: task.title,
    description: task.description,
    category: task.category,
    project: task.project,
    tags: task.tags.join(", "),
    start_date: task.start_date,
    due_date: task.due_date,
    estimated_minutes: task.estimated_minutes,
    importance: task.importance,
    is_completed: task.is_completed,
    is_fixed: task.is_fixed,
    recurrence: task.recurrence,
    recurrence_time_zone: task.recurrence_time_zone,
    notes: task.notes,
  };
}

export function TaskEditDialog({
  task,
  saving,
  error,
  onCancel,
  onSave,
}: TaskEditDialogProps) {
  const [draft, setDraft] = useState<EditDraft>(() => createDraft(task));
  const titleRef = useRef<HTMLInputElement>(null);
  const titleId = `edit-task-${task.id}-title`;

  useEffect(() => {
    titleRef.current?.focus();
    titleRef.current?.select();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.title.trim() || !draft.category.trim() || saving) return;

    await onSave({
      ...draft,
      title: draft.title.trim(),
      category: draft.category.trim(),
      project: draft.project?.trim() || null,
      tags: Array.from(
        new Set(
          draft.tags
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
        ),
      ),
      recurrence: draft.recurrence?.trim() || null,
      recurrence_time_zone: draft.recurrence
        ? draft.recurrence_time_zone?.trim() || null
        : null,
    });
  }

  return (
    <div
      className="dialog-backdrop"
      onKeyDown={(event) => handleDialogKeyboard(event, saving, onCancel)}
    >
      <section
        className="dialog-card task-editor"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">Task details</p>
            <h2 id={titleId}>Edit task</h2>
          </div>
          <button
            className="icon-button"
            type="button"
            aria-label="Close task editor"
            onClick={onCancel}
            disabled={saving}
          >
            ×
          </button>
        </div>

        <form onSubmit={submit} aria-busy={saving}>
          {error && (
            <p className="dialog-error" role="alert">
              {error}
            </p>
          )}
          <fieldset className="dialog-fields" disabled={saving}>
            <label>
              Title
              <input
                ref={titleRef}
                value={draft.title}
                onChange={(event) => setDraft({ ...draft, title: event.target.value })}
                required
                maxLength={200}
              />
            </label>

            <label>
              Description
              <textarea
                value={draft.description}
                onChange={(event) => setDraft({ ...draft, description: event.target.value })}
                rows={3}
              />
            </label>

            <div className="form-row">
              <label>
                Category
                <input
                  value={draft.category}
                  onChange={(event) => setDraft({ ...draft, category: event.target.value })}
                  required
                  maxLength={80}
                />
              </label>
              <label>
                Project
                <input
                  value={draft.project ?? ""}
                  onChange={(event) =>
                    setDraft({ ...draft, project: event.target.value || null })
                  }
                  placeholder="Optional project"
                  maxLength={200}
                />
              </label>
            </div>

            <label>
              Tags (comma separated)
              <input
                value={draft.tags}
                onChange={(event) => setDraft({ ...draft, tags: event.target.value })}
                placeholder="fictional, school"
              />
            </label>

            <div className="form-row">
              <label>
                Start date
                <input
                  type="date"
                  value={draft.start_date ?? ""}
                  onChange={(event) =>
                    setDraft({ ...draft, start_date: event.target.value || null })
                  }
                />
              </label>
              <label>
                Due date
                <input
                  type="date"
                  value={draft.due_date ?? ""}
                  onChange={(event) =>
                    setDraft({ ...draft, due_date: event.target.value || null })
                  }
                />
              </label>
            </div>

            <div className="form-row">
              <label>
                Estimated minutes
                <input
                  type="number"
                  min="5"
                  max="1440"
                  step="5"
                  value={draft.estimated_minutes}
                  onChange={(event) =>
                    setDraft({ ...draft, estimated_minutes: Number(event.target.value) })
                  }
                />
              </label>
              <label>
                Importance
                <select
                  value={draft.importance}
                  onChange={(event) =>
                    setDraft({ ...draft, importance: Number(event.target.value) })
                  }
                >
                  {[1, 2, 3, 4, 5].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="form-row">
              <label>
                Recurrence rule
                <input
                  value={draft.recurrence ?? ""}
                  onChange={(event) =>
                    setDraft({ ...draft, recurrence: event.target.value || null })
                  }
                  placeholder="FREQ=WEEKLY"
                  maxLength={500}
                />
              </label>
              <label>
                Recurrence time zone
                <input
                  value={draft.recurrence_time_zone ?? ""}
                  onChange={(event) =>
                    setDraft({
                      ...draft,
                      recurrence_time_zone: event.target.value || null,
                    })
                  }
                  placeholder="America/Phoenix"
                  maxLength={100}
                  disabled={!draft.recurrence}
                />
              </label>
            </div>

            <label>
              Notes
              <textarea
                value={draft.notes}
                onChange={(event) => setDraft({ ...draft, notes: event.target.value })}
                rows={3}
              />
            </label>

            <div className="checkbox-row">
              <label className="checkbox-control">
                <input
                  type="checkbox"
                  checked={draft.is_fixed}
                  onChange={(event) => setDraft({ ...draft, is_fixed: event.target.checked })}
                />
                Fixed commitment
              </label>
              <label className="checkbox-control">
                <input
                  type="checkbox"
                  checked={draft.is_completed}
                  onChange={(event) =>
                    setDraft({ ...draft, is_completed: event.target.checked })
                  }
                />
                Completed
              </label>
            </div>
          </fieldset>

          <div className="dialog-actions">
            <button className="secondary" type="button" onClick={onCancel} disabled={saving}>
              Cancel
            </button>
            <button className="primary" type="submit" disabled={saving}>
              {saving ? "Saving locally…" : "Save changes"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

