const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const ACTIVE_PROFILE_KEY = "aria.activeProfileId";
export const PROFILE_CHANGED_EVENT = "aria-profile-changed";

export function getActiveProfileId(): string {
  return localStorage.getItem(ACTIVE_PROFILE_KEY) ?? "local-default";
}

export function setActiveProfileId(profileId: string): void {
  localStorage.setItem(ACTIVE_PROFILE_KEY, profileId);
  window.dispatchEvent(new CustomEvent(PROFILE_CHANGED_EVENT, { detail: profileId }));
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Aria-Profile-ID": getActiveProfileId(),
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") detail = payload.detail;
    } catch {
      // The status and generic message remain useful when no JSON body is available.
    }
    throw new ApiError(`Aria API returned ${response.status}`, response.status, detail);
  }

  return response.status === 204 ? (undefined as T) : response.json();
}

