import { useRef, useState } from "react";
import { StatusMessage } from "../../components/StatusMessage";
import { DeleteEventDialog } from "./DeleteEventDialog";
import { EventEditDialog } from "./EventEditDialog";
import { EventForm } from "./EventForm";
import { EventList } from "./EventList";
import type { CalendarEvent, NewCalendarEvent } from "./types";
import { useEvents } from "./useEvents";

export function EventWorkspace() {
  const [editing, setEditing] = useState<CalendarEvent | null>(null);
  const [deleting, setDeleting] = useState<CalendarEvent | null>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const {
    events,
    loading,
    saving,
    updatingIds,
    deletingIds,
    error,
    notice,
    retry,
    createEvent,
    updateEvent,
    deleteEvent,
    clearFeedback,
  } = useEvents();

  function rememberFocus() {
    returnFocusRef.current = document.activeElement as HTMLElement | null;
  }

  function restoreFocus() {
    queueMicrotask(() => {
      if (returnFocusRef.current?.isConnected) returnFocusRef.current.focus();
    });
  }

  function openEditor(event: CalendarEvent) {
    rememberFocus();
    clearFeedback();
    setEditing(event);
  }

  function openDelete(event: CalendarEvent) {
    rememberFocus();
    clearFeedback();
    setDeleting(event);
  }

  async function saveEdited(payload: NewCalendarEvent): Promise<boolean> {
    if (!editing) return false;
    const saved = await updateEvent(editing.id, payload);
    if (saved) {
      setEditing(null);
      restoreFocus();
    }
    return saved;
  }

  async function confirmDelete(): Promise<boolean> {
    if (!deleting) return false;
    const deleted = await deleteEvent(deleting.id);
    if (deleted) {
      setDeleting(null);
      restoreFocus();
    }
    return deleted;
  }

  const pendingIds = new Set([...updatingIds, ...deletingIds]);

  return (
    <>
      <div className="workspace event-workspace">
        <section className="panel event-panel" aria-labelledby="events-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Local calendar</p>
              <h2 id="events-title">Upcoming events</h2>
            </div>
            <span className="count-badge">{events.length}</span>
          </div>
          {error && !editing && !deleting && (
            <StatusMessage message={error} onRetry={events.length === 0 ? retry : undefined} />
          )}
          {notice && <StatusMessage message={notice} tone="success" />}
          {loading ? (
            <p className="empty">Loading local events…</p>
          ) : events.length === 0 ? (
            <div className="empty">
              <strong>No events yet.</strong>
              <span>Add an appointment or commitment to test the calendar backend.</span>
            </div>
          ) : (
            <EventList
              events={events}
              pendingIds={pendingIds}
              onEdit={openEditor}
              onDelete={openDelete}
            />
          )}
        </section>

        <aside className="panel add-panel" aria-labelledby="add-event-title">
          <p className="eyebrow">Calendar capture</p>
          <h2 id="add-event-title">Add an event</h2>
          <EventForm saving={saving} submitLabel="Add event" onSubmit={createEvent} />
          <p className="privacy">Saved through the FastAPI event service into local SQLite.</p>
        </aside>
      </div>

      {editing && (
        <EventEditDialog
          event={editing}
          saving={updatingIds.has(editing.id)}
          error={error}
          onCancel={() => {
            setEditing(null);
            restoreFocus();
          }}
          onSave={saveEdited}
        />
      )}
      {deleting && (
        <DeleteEventDialog
          event={deleting}
          deleting={deletingIds.has(deleting.id)}
          error={error}
          onCancel={() => {
            setDeleting(null);
            restoreFocus();
          }}
          onConfirm={confirmDelete}
        />
      )}
    </>
  );
}
