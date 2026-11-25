import type { CalendarEvent } from "../events/types";
import type { Task } from "../tasks/types";

interface WeeklyAgendaProps {
  tasks: Task[];
  events: CalendarEvent[];
  loading: boolean;
  error?: string;
  today?: string;
}

interface AgendaItem {
  id: string;
  type: "event" | "task";
  title: string;
  meta: string;
  sortKey: string;
}

function localDateKey(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function dateInTimeZone(instant: string, timeZone: string): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(instant));
  const value = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return `${value("year")}-${value("month")}-${value("day")}`;
}

function eventDate(event: CalendarEvent): string | null {
  if (event.all_day) return event.start_date;
  if (!event.start_at) return null;
  return dateInTimeZone(event.start_at, event.time_zone);
}

function eventTime(event: CalendarEvent): string {
  if (event.all_day || !event.start_at) return "All day";
  return new Intl.DateTimeFormat(undefined, {
    timeZone: event.time_zone,
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(event.start_at));
}

function sevenDays(start: string): string[] {
  const anchor = new Date(`${start}T12:00:00`);
  return Array.from({ length: 7 }, (_, index) => {
    const day = new Date(anchor);
    day.setDate(anchor.getDate() + index);
    return localDateKey(day);
  });
}

function dayLabel(date: string, today: string): { weekday: string; date: string } {
  const value = new Date(`${date}T12:00:00`);
  return {
    weekday:
      date === today
        ? "Today"
        : new Intl.DateTimeFormat(undefined, { weekday: "short" }).format(value),
    date: new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(
      value,
    ),
  };
}

function itemsForDay(
  date: string,
  tasks: Task[],
  events: CalendarEvent[],
): AgendaItem[] {
  const eventItems: AgendaItem[] = events
    .filter((event) => eventDate(event) === date)
    .map((event) => ({
      id: `event-${event.id}`,
      type: "event",
      title: event.title,
      meta: `${eventTime(event)} · ${event.kind}${event.location ? ` · ${event.location}` : ""}`,
      sortKey: `0-${event.all_day ? "0000" : event.start_at ?? ""}-${event.id}`,
    }));
  const taskItems: AgendaItem[] = tasks
    .filter((task) => !task.is_completed && task.due_date === date)
    .map((task) => ({
      id: `task-${task.id}`,
      type: "task",
      title: task.title,
      meta: `Due today · priority ${task.priority.score} · ${task.estimated_minutes} min`,
      sortKey: `1-${String(1000 - task.priority.score).padStart(4, "0")}-${task.id}`,
    }));
  return [...eventItems, ...taskItems].sort((left, right) =>
    left.sortKey.localeCompare(right.sortKey),
  );
}

export function WeeklyAgenda({
  tasks,
  events,
  loading,
  error = "",
  today = localDateKey(new Date()),
}: WeeklyAgendaProps) {
  const days = sevenDays(today);
  const itemCount = days.reduce(
    (count, day) => count + itemsForDay(day, tasks, events).length,
    0,
  );

  return (
    <section className="panel weekly-agenda" aria-labelledby="weekly-agenda-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Next seven days</p>
          <h2 id="weekly-agenda-title">Weekly agenda</h2>
        </div>
        <span className="count-badge" aria-label={`${itemCount} scheduled items`}>
          {itemCount}
        </span>
      </div>

      {error && <p className="agenda-error" role="alert">{error}</p>}
      {loading ? (
        <p className="empty" role="status">Building your local agenda…</p>
      ) : (
        <ol className="agenda-days">
          {days.map((day) => {
            const label = dayLabel(day, today);
            const items = itemsForDay(day, tasks, events);
            return (
              <li className={day === today ? "agenda-day agenda-today" : "agenda-day"} key={day}>
                <header>
                  <strong>{label.weekday}</strong>
                  <span>{label.date}</span>
                </header>
                {items.length === 0 ? (
                  <p className="agenda-open">Open</p>
                ) : (
                  <ul>
                    {items.map((item) => (
                      <li className={`agenda-item agenda-${item.type}`} key={item.id}>
                        <span>{item.type}</span>
                        <strong>{item.title}</strong>
                        <small>{item.meta}</small>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            );
          })}
        </ol>
      )}
      {!loading && !error && itemCount === 0 && (
        <p className="agenda-summary">Nothing is scheduled yet. Unallocated time is a valid plan.</p>
      )}
    </section>
  );
}
