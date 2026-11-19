import { request } from "../../lib/api";
import type { CalendarEvent, CalendarEventUpdate, NewCalendarEvent } from "./types";

export const eventApi = {
  list: () => request<CalendarEvent[]>("/api/events"),
  create: (event: NewCalendarEvent) =>
    request<CalendarEvent>("/api/events", {
      method: "POST",
      body: JSON.stringify(event),
    }),
  update: (id: number, event: CalendarEventUpdate) =>
    request<CalendarEvent>(`/api/events/${id}`, {
      method: "PATCH",
      body: JSON.stringify(event),
    }),
  remove: (id: number) => request<void>(`/api/events/${id}`, { method: "DELETE" }),
};
