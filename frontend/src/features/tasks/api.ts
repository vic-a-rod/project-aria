import { request } from "../../lib/api";
import type { NewTask, Task } from "./types";

export const taskApi = {
  list: () => request<Task[]>("/api/tasks"),
  create: (task: NewTask) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(task) }),
  setCompleted: (id: number, is_completed: boolean) =>
    request<Task>(`/api/tasks/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_completed }),
    }),
};

