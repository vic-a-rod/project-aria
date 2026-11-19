import { request } from "../../lib/api";
import type { NewProfile, Profile } from "./types";

export const profileApi = {
  list: () => request<Profile[]>("/api/profiles"),
  create: (profile: NewProfile) =>
    request<Profile>("/api/profiles", {
      method: "POST",
      body: JSON.stringify(profile),
    }),
};
