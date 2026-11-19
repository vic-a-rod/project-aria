import { useState } from "react";
import { handleDialogKeyboard } from "../../components/dialogKeyboard";
import { EventForm } from "./EventForm";
import type { CalendarEvent, NewCalendarEvent } from "./types";

type EventEditDialogProps = {
  event: CalendarEvent;
  saving: boolean;
  error?: string;
  onCancel: () => void;
  onSave: (payload: NewCalendarEvent) => Promise<boolean>;
};

export function EventEditDialog({
  event,
  saving,
  error,
  onCancel,
  onSave,
}: EventEditDialogProps) {
  const [titleId] = useState(() => `edit-event-${event.id}-title`);
  return (
    <div
      className="dialog-backdrop"
      onKeyDown={(keyboardEvent) => handleDialogKeyboard(keyboardEvent, saving, onCancel)}
    >
      <section className="dialog-card" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="dialog-heading">
          <div>
            <p className="eyebrow">Calendar details</p>
            <h2 id={titleId}>Edit event</h2>
          </div>
          <button
            className="icon-button"
            type="button"
            aria-label="Close event editor"
            onClick={onCancel}
            disabled={saving}
          >
            ×
          </button>
        </div>
        {error && <p className="dialog-error" role="alert">{error}</p>}
        <EventForm event={event} saving={saving} submitLabel="Save event" onSubmit={onSave} />
      </section>
    </div>
  );
}
