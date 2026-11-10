import type { NewTask, Task } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!response.ok) {
    throw new Error(`Aria API returned ${response.status}`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  listTasks: () => request<Task[]>("/api/tasks"),
  createTask: (task: NewTask) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(task) }),
  setCompleted: (id: number, is_completed: boolean) =>
    request<Task>(`/api/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_completed }),
    }),
};

