import type { NewTask } from "./types";

export const taskCategories = [
  "Personal",
  "Education",
  "Career",
  "Software projects",
  "Appointments",
] as const;

export function createEmptyTask(): NewTask {
  return {
    title: "",
    category: "Personal",
    due_date: null,
    estimated_minutes: 30,
    importance: 3,
  };
}

