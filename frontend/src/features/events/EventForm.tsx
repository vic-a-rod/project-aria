import { FormEvent, useEffect, useRef, useState } from "react";
import {
  allDayDefaults,
  createEmptyEventDraft,
  draftFromEvent,
  eventPayload,
  timedDefaults,
  type EventDraft,
} from "./eventDraft";
import type { CalendarEvent, NewCalendarEvent } from "./types";

type EventFormProps = {
  event?: CalendarEvent;
  saving: boolean;
  submitLabel: string;
  onSubmit: (payload: NewCalendarEvent) => Promise<boolean>;
};

export function EventForm({ event, saving, submitLabel, onSubmit }: EventFormProps) {
  const [draft, setDraft] = useState<EventDraft>(() =>
    event ? draftFromEvent(event) : createEmptyEventDraft(),
  );
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (event) {
      titleRef.current?.focus();
      titleRef.current?.select();
    }
  }, [event]);

  async function submit(formEvent: FormEvent<HTMLFormElement>) {
    formEvent.preventDefault();
    if (!draft.title.trim() || saving) return;
    const saved = await onSubmit(eventPayload(draft, event));
    if (saved && !event) setDraft(createEmptyEventDraft());
  }

  function toggleAllDay(allDay: boolean) {
    setDraft({ ...draft, allDay, ...(allDay ? allDayDefaults() : timedDefaults()) });
  }

  return (
    <form className="event-form" onSubmit={submit} aria-busy={saving}>
      <fieldset className="dialog-fields" disabled={saving}>
        <label>
          Event title
          <input
            ref={titleRef}
            value={draft.title}
            onChange={(input) => setDraft({ ...draft, title: input.target.value })}
            placeholder="e.g. Fictional advising appointment"
            required
            maxLength={200}
          />
        </label>

        <div className="form-row">
          <label>
            Type
            <select
              value={draft.kind}
              onChange={(input) =>
                setDraft({ ...draft, kind: input.target.value as EventDraft["kind"] })
              }
            >
              <option value="event">Event</option>
              <option value="appointment">Appointment</option>
              <option value="commitment">Commitment</option>
            </select>
          </label>
          <label>
            Location
            <input
              value={draft.location}
              onChange={(input) => setDraft({ ...draft, location: input.target.value })}
              maxLength={300}
            />
          </label>
        </div>

        <label className="checkbox-control">
          <input
            type="checkbox"
            checked={draft.allDay}
            onChange={(input) => toggleAllDay(input.target.checked)}
          />
          All-day event
        </label>

        <div className="form-row">
          <label>
            Start
            <input
              type={draft.allDay ? "date" : "datetime-local"}
              value={draft.start}
              onChange={(input) => setDraft({ ...draft, start: input.target.value })}
              required
            />
          </label>
          <label>
            End {draft.allDay && <span className="field-hint">(exclusive)</span>}
            <input
              type={draft.allDay ? "date" : "datetime-local"}
              value={draft.end}
              onChange={(input) => setDraft({ ...draft, end: input.target.value })}
              required
            />
          </label>
        </div>

        <div className="checkbox-row">
          <label className="checkbox-control">
            <input
              type="checkbox"
              checked={draft.isFixed}
              onChange={(input) => setDraft({ ...draft, isFixed: input.target.checked })}
            />
            Fixed time
          </label>
          <label className="checkbox-control">
            <input
              type="checkbox"
              checked={draft.blocksTime}
              onChange={(input) => setDraft({ ...draft, blocksTime: input.target.checked })}
            />
            Blocks availability
          </label>
        </div>
      </fieldset>

      <button className="primary" type="submit" disabled={saving}>
        {saving ? "Saving locally…" : submitLabel}
      </button>
    </form>
  );
}
