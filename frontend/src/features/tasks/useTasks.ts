import { useCallback, useEffect, useState } from "react";
import { taskApi } from "./api";
import type { NewTask, Task } from "./types";

function sortTasks(tasks: Task[]): Task[] {
  return [...tasks].sort((left, right) => {
    if (left.is_completed !== right.is_completed) return left.is_completed ? 1 : -1;
    return right.priority.score - left.priority.score;
  });
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof Error && error.message ? `${fallback} ${error.message}.` : fallback;
}

export function useTasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<Set<number>>(() => new Set());
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setTasks(sortTasks(await taskApi.list()));
    } catch (loadError) {
      setError(
        messageFor(
          loadError,
          "The local API is unavailable. Start the backend, then try again.",
        ),
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;

    taskApi
      .list()
      .then((loadedTasks) => {
        if (active) setTasks(sortTasks(loadedTasks));
      })
      .catch((loadError) => {
        if (active) {
          setError(
            messageFor(
              loadError,
              "The local API is unavailable. Start the backend, then try again.",
            ),
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function createTask(draft: NewTask): Promise<boolean> {
    setSaving(true);
    setError("");
    try {
      const created = await taskApi.create({ ...draft, title: draft.title.trim() });
      setTasks((current) => sortTasks([created, ...current]));
      return true;
    } catch (createError) {
      setError(messageFor(createError, "Aria could not save that task."));
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function toggleCompleted(task: Task): Promise<void> {
    setUpdatingIds((current) => new Set(current).add(task.id));
    setError("");
    try {
      const updated = await taskApi.setCompleted(task.id, !task.is_completed);
      setTasks((current) =>
        sortTasks(current.map((item) => (item.id === task.id ? updated : item))),
      );
    } catch (updateError) {
      setError(messageFor(updateError, "Aria could not update that task."));
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(task.id);
        return next;
      });
    }
  }

  return {
    tasks,
    loading,
    saving,
    updatingIds,
    error,
    retry: load,
    createTask,
    toggleCompleted,
  };
}

