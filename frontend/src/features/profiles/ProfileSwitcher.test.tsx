import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getActiveProfileId, PROFILE_CHANGED_EVENT } from "../../lib/api";
import { profileApi } from "./api";
import { ProfileSwitcher } from "./ProfileSwitcher";

vi.mock("./api", () => ({
  profileApi: { list: vi.fn(), create: vi.fn() },
}));

const mockedProfileApi = vi.mocked(profileApi);
const defaultProfile = {
  id: "local-default",
  display_name: "Local User",
  created_at: "2026-11-18T19:00:00Z",
  updated_at: "2026-11-18T19:00:00Z",
};

describe("ProfileSwitcher", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockedProfileApi.list.mockResolvedValue([defaultProfile]);
  });

  it("creates and activates a local profile without login", async () => {
    const user = userEvent.setup();
    const second = { ...defaultProfile, id: "profile-two", display_name: "Demo Partner" };
    mockedProfileApi.create.mockResolvedValue(second);
    const changed = vi.fn();
    window.addEventListener(PROFILE_CHANGED_EVENT, changed);

    render(<ProfileSwitcher />);
    await screen.findByRole("option", { name: "Local User" });
    await user.type(screen.getByLabelText("New profile name"), "Demo Partner");
    await user.click(screen.getByRole("button", { name: "Add profile" }));

    await waitFor(() =>
      expect(mockedProfileApi.create).toHaveBeenCalledWith({ display_name: "Demo Partner" }),
    );
    expect(screen.getByLabelText("Using Aria as")).toHaveValue("profile-two");
    expect(getActiveProfileId()).toBe("profile-two");
    expect(changed).toHaveBeenCalled();
    window.removeEventListener(PROFILE_CHANGED_EVENT, changed);
  });
});
