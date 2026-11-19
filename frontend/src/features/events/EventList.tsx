import type { CalendarEvent } from "./types";

type EventListProps = {
  events: CalendarEvent[];
  pendingIds: Set<number>;
  onEdit: (event: CalendarEvent) => void;
  onDelete: (event: CalendarEvent) => void;
};

function eventTime(event: CalendarEvent): string {
  if (event.all_day) {
    return `${event.start_date} · all day`;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(event.start_at ?? ""));
}

export function EventList({ events, pendingIds, onEdit, onDelete }: EventListProps) {
  return (
    <ul className="event-list">
      {events.map((event) => {
        const pending = pendingIds.has(event.id);
        return (
          <li key={event.id}>
            <div className="event-date" aria-hidden="true">
              {event.all_day ? "Day" : new Date(event.start_at ?? "").getDate()}
            </div>
            <div className="event-copy">
              <strong>{event.title}</strong>
              <span>
                {eventTime(event)}
                {event.location ? ` · ${event.location}` : ""}
              </span>
              <small>
                {event.kind} · {event.is_fixed ? "fixed" : "flexible"} · {event.calendar_name}
              </small>
            </div>
            <div className="event-actions">
              <button
                className="text-button"
                type="button"
                onClick={() => onEdit(event)}
                disabled={pending}
                aria-label={`Edit event ${event.title}`}
              >
                Edit
              </button>
              <button
                className="text-button danger-text"
                type="button"
                onClick={() => onDelete(event)}
                disabled={pending}
                aria-label={`Delete event ${event.title}`}
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
