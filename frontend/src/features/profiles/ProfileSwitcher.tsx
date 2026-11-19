import { FormEvent, useEffect, useState } from "react";
import { getActiveProfileId, setActiveProfileId } from "../../lib/api";
import { profileApi } from "./api";
import type { Profile } from "./types";

export function ProfileSwitcher() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [activeId, setActiveId] = useState(getActiveProfileId);
  const [displayName, setDisplayName] = useState("");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    profileApi
      .list()
      .then((loaded) => {
        setProfiles(loaded);
        if (!loaded.some((profile) => profile.id === getActiveProfileId()) && loaded[0]) {
          setActiveId(loaded[0].id);
          setActiveProfileId(loaded[0].id);
        }
      })
      .catch(() => setError("Profiles unavailable"));
  }, []);

  function choose(profileId: string) {
    setActiveId(profileId);
    setActiveProfileId(profileId);
  }

  async function createProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = displayName.trim();
    if (!name || adding) return;
    setAdding(true);
    setError("");
    try {
      const created = await profileApi.create({ display_name: name });
      setProfiles((current) => [...current, created]);
      setDisplayName("");
      choose(created.id);
    } catch {
      setError("Could not create profile");
    } finally {
      setAdding(false);
    }
  }

  return (
    <section className="profile-switcher" aria-label="Local profile">
      <label>
        Using Aria as
        <select value={activeId} onChange={(event) => choose(event.target.value)}>
          {profiles.map((profile) => (
            <option key={profile.id} value={profile.id}>
              {profile.display_name}
            </option>
          ))}
        </select>
      </label>
      <form onSubmit={createProfile}>
        <label className="sr-only" htmlFor="new-profile-name">
          New profile name
        </label>
        <input
          id="new-profile-name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          placeholder="New profile name"
          maxLength={100}
        />
        <button type="submit" disabled={adding || !displayName.trim()}>
          {adding ? "Adding…" : "Add profile"}
        </button>
      </form>
      {error && <span className="profile-error">{error}</span>}
    </section>
  );
}
