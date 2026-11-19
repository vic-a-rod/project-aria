import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { eventApi } from "./api";
import { EventWorkspace } from "./EventWorkspace";
import type { CalendarEvent } from "./types";

vi.mock("./api", () => ({
  eventApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
}));

const mockedEventApi = vi.mocked(eventApi);
const fictionalEvent: CalendarEvent = {
  id: 7,
  title: "Fictional demo appointment",
  description: "",
  kind: "appointment",
  all_day: false,
  start_at: "2030-01-15T17:00:00Z",
  end_at: "2030-01-15T18:00:00Z",
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
};

describe("EventWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedEventApi.list.mockResolvedValue([]);
  });

  it("creates and deletes an event through the dashboard", async () => {
    const user = userEvent.setup();
    mockedEventApi.create.mockResolvedValue(fictionalEvent);
    mockedEventApi.remove.mockResolvedValue(undefined);
    render(<EventWorkspace />);
    await screen.findByText("No events yet.");

    await user.type(screen.getByLabelText("Event title"), fictionalEvent.title);
    await user.selectOptions(screen.getByLabelText("Type"), "appointment");
    await user.type(screen.getByLabelText("Location"), fictionalEvent.location);
    await user.click(screen.getByRole("button", { name: "Add event" }));

    expect(await screen.findByText(fictionalEvent.title)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: `Delete event ${fictionalEvent.title}` }));
    const dialog = screen.getByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Delete event" }));

    await waitFor(() => expect(mockedEventApi.remove).toHaveBeenCalledWith(fictionalEvent.id));
    expect(screen.queryByText(fictionalEvent.title)).not.toBeInTheDocument();
  });
});
