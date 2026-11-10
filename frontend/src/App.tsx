import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import type { NewTask, Task } from "./types";

const emptyTask: NewTask = {
  title: "",
  category: "Personal",
  due_date: null,
  estimated_minutes: 30,
  importance: 3,
};

function App() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [draft, setDraft] = useState<NewTask>(emptyTask);
  const [filter, setFilter] = useState("All");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listTasks()
      .then(setTasks)
      .catch(() => setError("The local API is unavailable. Start the backend and refresh."))
      .finally(() => setLoading(false));
  }, []);

  const categories = useMemo(
    () => ["All", ...Array.from(new Set(tasks.map((task) => task.category)))],
    [tasks],
  );
  const visible = tasks.filter((task) => filter === "All" || task.category === filter);
  const openTasks = tasks.filter((task) => !task.is_completed);
  const focusMinutes = openTasks.reduce((sum, task) => sum + task.estimated_minutes, 0);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!draft.title.trim()) return;
    setError("");
    try {
      const created = await api.createTask(draft);
      setTasks((current) => [created, ...current]);
      setDraft(emptyTask);
    } catch {
      setError("Jarvis could not save that task.");
    }
  }

  async function toggle(task: Task) {
    try {
      const updated = await api.setCompleted(task.id, !task.is_completed);
      setTasks((current) => current.map((item) => (item.id === task.id ? updated : item)));
    } catch {
      setError("Jarvis could not update that task.");
    }
  }

  return (
    <main>
      <header>
        <div className="brand"><span>J</span> Jarvis</div>
        <p className="eyebrow">Sustainable productivity, one clear choice at a time.</p>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">Today’s overview</p>
          <h1>Make space for what matters.</h1>
          <p className="subtle">Jarvis ranks responsibilities with clear rules while leaving room for life.</p>
        </div>
        <div className="metrics">
          <article><strong>{openTasks.length}</strong><span>open tasks</span></article>
          <article><strong>{Math.round(focusMinutes / 60 * 10) / 10}h</strong><span>estimated focus</span></article>
          <article><strong>{openTasks[0]?.priority.score ?? 0}</strong><span>top priority</span></article>
        </div>
      </section>

      <div className="workspace">
        <section className="panel task-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Prioritized queue</p><h2>Your responsibilities</h2></div>
            <select value={filter} onChange={(event) => setFilter(event.target.value)}>
              {categories.map((category) => <option key={category}>{category}</option>)}
            </select>
          </div>
          {error && <p className="error">{error}</p>}
          {loading ? <p className="empty">Loading your local tasks…</p> : visible.length === 0 ? (
            <p className="empty">No tasks here yet. Add one without overplanning the day.</p>
          ) : (
            <ul className="task-list">
              {visible.map((task) => (
                <li key={task.id} className={task.is_completed ? "completed" : ""}>
                  <button className="check" onClick={() => toggle(task)} aria-label={`Mark ${task.title} complete`}>
                    {task.is_completed ? "✓" : ""}
                  </button>
                  <div className="task-copy">
                    <strong>{task.title}</strong>
                    <span>{task.category} · {task.estimated_minutes} min{task.due_date ? ` · due ${task.due_date}` : ""}</span>
                    <details><summary>Why this priority?</summary>{task.priority.reasons.map((reason) => <p key={reason}>{reason}</p>)}</details>
                  </div>
                  <div className="score"><strong>{task.priority.score}</strong><span>priority</span></div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="panel add-panel">
          <p className="eyebrow">Quick capture</p>
          <h2>Add a task</h2>
          <form onSubmit={submit}>
            <label>What needs doing?<input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="e.g. Review course syllabus" /></label>
            <label>Category<select value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })}><option>Personal</option><option>Education</option><option>Career</option><option>Software projects</option><option>Appointments</option></select></label>
            <label>Due date<input type="date" value={draft.due_date ?? ""} onChange={(e) => setDraft({ ...draft, due_date: e.target.value || null })} /></label>
            <div className="form-row">
              <label>Minutes<input type="number" min="5" max="1440" value={draft.estimated_minutes} onChange={(e) => setDraft({ ...draft, estimated_minutes: Number(e.target.value) })} /></label>
              <label>Importance<select value={draft.importance} onChange={(e) => setDraft({ ...draft, importance: Number(e.target.value) })}>{[1,2,3,4,5].map((value) => <option key={value}>{value}</option>)}</select></label>
            </div>
            <button className="primary" type="submit">Add to Jarvis</button>
          </form>
          <p className="privacy">Stored locally. No account or cloud sync.</p>
        </aside>
      </div>
    </main>
  );
}

export default App;

