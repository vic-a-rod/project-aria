import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { CalendarEvent } from "../events/types";
import type { Task } from "../tasks/types";
import { WeeklyAgenda } from "./WeeklyAgenda";

function fictionalTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 41,
    title: "Submit fictional project outline",
    description: "",
    category: "Education",
    project: null,
    tags: ["fictional"],
    start_date: null,
    due_date: "2030-01-15",
    estimated_minutes: 45,
    importance: 4,
    is_completed: false,
    completed_at: null,
    is_fixed: false,
    recurrence: null,
    recurrence_time_zone: null,
    notes: "",
    created_at: "2029-12-01T12:00:00Z",
    updated_at: "2029-12-01T12:00:00Z",
    priority: { score: 62, reasons: ["Fictional deadline is approaching."] },
    ...overrides,
  };
}

function fictionalEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: 7,
    title: "Fictional demo appointment",
    description: "",
    kind: "appointment",
    all_day: false,
    start_at: "2030-01-16T18:00:00Z",
    end_at: "2030-01-16T19:00:00Z",
    start_date: null,
    end_date: null,
    time_zone: "America/Phoenix",
    is_fixed: true,
    blocks_time: true,
    recurrence_rule: null,
    recurrence_time_zone: null,
    location: "Demo room",
    calendar_name: "Aria",
    source_type: "local",
    source_reference: null,
    created_at: "2029-12-01T12:00:00Z",
    updated_at: "2029-12-01T12:00:00Z",
    ...overrides,
  };
}

describe("WeeklyAgenda", () => {
  it("groups saved task deadlines and events into the next seven local days", () => {
    render(
      <WeeklyAgenda
        today="2030-01-15"
        loading={false}
        tasks={[
          fictionalTask(),
          fictionalTask({
            id: 42,
            title: "Completed fictional task",
            due_date: "2030-01-16",
            is_completed: true,
          }),
          fictionalTask({ id: 43, title: "Later fictional task", due_date: "2030-02-10" }),
        ]}
        events={[fictionalEvent()]}
      />,
    );

    expect(screen.getByLabelText("2 scheduled items")).toHaveTextContent("2");
    const today = screen.getByText("Today").closest<HTMLElement>(".agenda-day");
    expect(today).not.toBeNull();
    expect(within(today!).getByText("Submit fictional project outline")).toBeInTheDocument();
    expect(within(today!).getByText(/priority 62 · 45 min/i)).toBeInTheDocument();

    const appointment = screen.getByText("Fictional demo appointment");
    const appointmentDay = appointment.closest<HTMLElement>(".agenda-day");
    expect(appointmentDay).not.toBeNull();
    expect(within(appointmentDay!).getByText(/appointment · Demo room/i)).toBeInTheDocument();
    expect(screen.queryByText("Completed fictional task")).not.toBeInTheDocument();
    expect(screen.queryByText("Later fictional task")).not.toBeInTheDocument();
  });

  it("treats an empty week as valid unallocated time", () => {
    render(
      <WeeklyAgenda
        today="2030-01-15"
        loading={false}
        tasks={[]}
        events={[]}
      />,
    );

    expect(screen.getAllByText("Open")).toHaveLength(7);
    expect(screen.getByText(/Unallocated time is a valid plan/i)).toBeInTheDocument();
  });

  it("announces loading and upstream API errors", () => {
    const { rerender } = render(
      <WeeklyAgenda today="2030-01-15" loading tasks={[]} events={[]} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Building your local agenda");

    rerender(
      <WeeklyAgenda
        today="2030-01-15"
        loading={false}
        tasks={[]}
        events={[]}
        error="Aria could not load local events."
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("could not load local events");
  });
});
