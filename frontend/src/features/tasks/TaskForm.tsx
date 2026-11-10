import { FormEvent, useState } from "react";
import { createEmptyTask, taskCategories } from "./taskDefaults";
import type { NewTask } from "./types";

type TaskFormProps = {
  saving: boolean;
  onCreate: (draft: NewTask) => Promise<boolean>;
};

export function TaskForm({ saving, onCreate }: TaskFormProps) {
  const [draft, setDraft] = useState<NewTask>(() => createEmptyTask());

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft.title.trim() || saving) return;

    if (await onCreate(draft)) {
      setDraft(createEmptyTask());
    }
  }

  return (
    <form onSubmit={submit} aria-busy={saving}>
      <label>
        What needs doing?
        <input
          value={draft.title}
          onChange={(event) => setDraft({ ...draft, title: event.target.value })}
          placeholder="e.g. Review a fictional course syllabus"
          autoComplete="off"
          required
          maxLength={200}
          disabled={saving}
        />
      </label>

      <label>
        Category
        <select
          value={draft.category}
          onChange={(event) => setDraft({ ...draft, category: event.target.value })}
          disabled={saving}
        >
          {taskCategories.map((category) => (
            <option key={category}>{category}</option>
          ))}
        </select>
      </label>

      <label>
        Due date
        <input
          type="date"
          value={draft.due_date ?? ""}
          onChange={(event) => setDraft({ ...draft, due_date: event.target.value || null })}
          disabled={saving}
        />
      </label>

      <div className="form-row">
        <label>
          Minutes
          <input
            type="number"
            min="5"
            max="1440"
            step="5"
            value={draft.estimated_minutes}
            onChange={(event) =>
              setDraft({ ...draft, estimated_minutes: Number(event.target.value) })
            }
            disabled={saving}
          />
        </label>
        <label>
          Importance
          <select
            value={draft.importance}
            onChange={(event) => setDraft({ ...draft, importance: Number(event.target.value) })}
            disabled={saving}
          >
            {[1, 2, 3, 4, 5].map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
      </div>

      <button className="primary" type="submit" disabled={saving}>
        {saving ? "Saving locally…" : "Add to Aria"}
      </button>
    </form>
  );
}

