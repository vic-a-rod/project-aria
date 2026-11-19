import type { CalendarEvent, EventKind, NewCalendarEvent } from "./types";

export type EventDraft = {
  title: string;
  kind: EventKind;
  allDay: boolean;
  start: string;
  end: string;
  location: string;
  isFixed: boolean;
  blocksTime: boolean;
};

function pad(value: number): string {
  return String(value).padStart(2, "0");
}

function localDateTime(value: Date): string {
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

function localDate(value: Date): string {
  return localDateTime(value).slice(0, 10);
}

export function createEmptyEventDraft(): EventDraft {
  const start = new Date();
  start.setSeconds(0, 0);
  start.setMinutes(0);
  start.setHours(start.getHours() + 1);
  const end = new Date(start.getTime() + 60 * 60 * 1000);
  return {
    title: "",
    kind: "event",
    allDay: false,
    start: localDateTime(start),
    end: localDateTime(end),
    location: "",
    isFixed: true,
    blocksTime: true,
  };
}

export function draftFromEvent(event: CalendarEvent): EventDraft {
  return {
    title: event.title,
    kind: event.kind,
    allDay: event.all_day,
    start: event.all_day
      ? (event.start_date ?? "")
      : localDateTime(new Date(event.start_at ?? "")),
    end: event.all_day
      ? (event.end_date ?? "")
      : localDateTime(new Date(event.end_at ?? "")),
    location: event.location,
    isFixed: event.is_fixed,
    blocksTime: event.blocks_time,
  };
}

export function eventPayload(
  draft: EventDraft,
  existing?: CalendarEvent,
): NewCalendarEvent {
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  return {
    title: draft.title.trim(),
    description: existing?.description ?? "",
    kind: draft.kind,
    all_day: draft.allDay,
    start_at: draft.allDay ? null : new Date(draft.start).toISOString(),
    end_at: draft.allDay ? null : new Date(draft.end).toISOString(),
    start_date: draft.allDay ? draft.start : null,
    end_date: draft.allDay ? draft.end : null,
    time_zone: timeZone,
    is_fixed: draft.isFixed,
    blocks_time: draft.blocksTime,
    recurrence_rule: existing?.recurrence_rule ?? null,
    recurrence_time_zone: existing?.recurrence_time_zone ?? null,
    location: draft.location.trim(),
    calendar_name: existing?.calendar_name ?? "Aria",
    source_type: existing?.source_type ?? "local",
    source_reference: existing?.source_reference ?? null,
  };
}

export function allDayDefaults(): Pick<EventDraft, "start" | "end"> {
  const start = new Date();
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return { start: localDate(start), end: localDate(end) };
}

export function timedDefaults(): Pick<EventDraft, "start" | "end"> {
  const draft = createEmptyEventDraft();
  return { start: draft.start, end: draft.end };
}
