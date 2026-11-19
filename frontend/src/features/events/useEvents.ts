import { useCallback, useEffect, useState } from "react";
import { eventApi } from "./api";
import { PROFILE_CHANGED_EVENT } from "../../lib/api";
import type { CalendarEvent, CalendarEventUpdate, NewCalendarEvent } from "./types";

function eventAnchor(event: CalendarEvent): string {
  return event.start_at ?? event.start_date ?? "";
}

function sortEvents(events: CalendarEvent[]): CalendarEvent[] {
  return [...events].sort((left, right) => eventAnchor(left).localeCompare(eventAnchor(right)));
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? `${fallback} ${error.message}.` : fallback;
}

export function useEvents() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<Set<number>>(() => new Set());
  const [deletingIds, setDeletingIds] = useState<Set<number>>(() => new Set());
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setEvents(sortEvents(await eventApi.list()));
    } catch (loadError) {
      setError(messageFor(loadError, "Aria could not load local events."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    eventApi
      .list()
      .then((loaded) => {
        if (active) setEvents(sortEvents(loaded));
      })
      .catch((loadError) => {
        if (active) setError(messageFor(loadError, "Aria could not load local events."));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const reload = () => void load();
    window.addEventListener(PROFILE_CHANGED_EVENT, reload);
    return () => window.removeEventListener(PROFILE_CHANGED_EVENT, reload);
  }, [load]);

  async function createEvent(draft: NewCalendarEvent): Promise<boolean> {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const created = await eventApi.create(draft);
      setEvents((current) => sortEvents([...current, created]));
      setNotice("Event added to this local workspace.");
      return true;
    } catch (createError) {
      setError(messageFor(createError, "Aria could not save that event."));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function updateEvent(id: number, changes: CalendarEventUpdate): Promise<boolean> {
    setUpdatingIds((current) => new Set(current).add(id));
    setError("");
    setNotice("");
    try {
      const updated = await eventApi.update(id, changes);
      setEvents((current) =>
        sortEvents(current.map((event) => (event.id === id ? updated : event))),
      );
      setNotice("Event changes saved locally.");
      return true;
    } catch (updateError) {
      setError(messageFor(updateError, "Aria could not save those event changes."));
      return false;
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  }

  async function deleteEvent(id: number): Promise<boolean> {
    setDeletingIds((current) => new Set(current).add(id));
    setError("");
    setNotice("");
    try {
      await eventApi.remove(id);
      setEvents((current) => current.filter((event) => event.id !== id));
      setNotice("Event deleted from this local workspace.");
      return true;
    } catch (deleteError) {
      setError(messageFor(deleteError, "Aria could not delete that event."));
      return false;
    } finally {
      setDeletingIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  }

  return {
    events,
    loading,
    saving,
    updatingIds,
    deletingIds,
    error,
    notice,
    retry: load,
    createEvent,
    updateEvent,
    deleteEvent,
    clearFeedback: () => {
      setError("");
      setNotice("");
    },
  };
}
