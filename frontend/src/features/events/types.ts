export type EventKind = "event" | "appointment" | "commitment";
export type EventSource = "local" | "calendar" | "email" | "import";

export type CalendarEvent = {
  id: number;
  title: string;
  description: string;
  kind: EventKind;
  all_day: boolean;
  start_at: string | null;
  end_at: string | null;
  start_date: string | null;
  end_date: string | null;
  time_zone: string;
  is_fixed: boolean;
  blocks_time: boolean;
  recurrence_rule: string | null;
  recurrence_time_zone: string | null;
  location: string;
  calendar_name: string;
  source_type: EventSource;
  source_reference: string | null;
  created_at: string;
  updated_at: string;
};

export type NewCalendarEvent = Omit<CalendarEvent, "id" | "created_at" | "updated_at">;
export type CalendarEventUpdate = Partial<NewCalendarEvent>;
