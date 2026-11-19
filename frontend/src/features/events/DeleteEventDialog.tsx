import { useEffect, useRef } from "react";
import { handleDialogKeyboard } from "../../components/dialogKeyboard";
import type { CalendarEvent } from "./types";

type DeleteEventDialogProps = {
  event: CalendarEvent;
  deleting: boolean;
  error?: string;
  onCancel: () => void;
  onConfirm: () => Promise<boolean>;
};

export function DeleteEventDialog({
  event,
  deleting,
  error,
  onCancel,
  onConfirm,
}: DeleteEventDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = `delete-event-${event.id}-title`;
  useEffect(() => cancelRef.current?.focus(), []);

  return (
    <div
      className="dialog-backdrop"
      onKeyDown={(keyboardEvent) => handleDialogKeyboard(keyboardEvent, deleting, onCancel)}
    >
      <section
        className="dialog-card confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <p className="eyebrow">Confirm deletion</p>
        <h2 id={titleId}>Delete “{event.title}”?</h2>
        <p>This removes the event from the local Aria calendar and cannot be undone.</p>
        {error && <p className="dialog-error" role="alert">{error}</p>}
        <div className="dialog-actions">
          <button
            ref={cancelRef}
            className="secondary"
            type="button"
            onClick={onCancel}
            disabled={deleting}
          >
            Keep event
          </button>
          <button
            className="danger"
            type="button"
            onClick={() => void onConfirm()}
            disabled={deleting}
          >
            {deleting ? "Deleting locally…" : "Delete event"}
          </button>
        </div>
      </section>
    </div>
  );
}
