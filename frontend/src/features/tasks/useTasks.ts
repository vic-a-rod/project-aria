import { useCallback, useEffect, useState } from "react";
import { taskApi } from "./api";
import type { NewTask, Task, TaskUpdate } from "./types";

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
  const [deletingIds, setDeletingIds] = useState<Set<number>>(() => new Set());
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    setNotice("");
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
    setNotice("");
    try {
      const created = await taskApi.create({ ...draft, title: draft.title.trim() });
      setTasks((current) => sortTasks([created, ...current]));
      setNotice("Task added to this local workspace.");
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
    setNotice("");
    try {
      const updated = await taskApi.setCompleted(task.id, !task.is_completed);
      setTasks((current) =>
        sortTasks(current.map((item) => (item.id === task.id ? updated : item))),
      );
      setNotice(updated.is_completed ? "Task completed." : "Task reopened.");
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

  async function updateTask(taskId: number, changes: TaskUpdate): Promise<boolean> {
    setUpdatingIds((current) => new Set(current).add(taskId));
    setError("");
    setNotice("");
    try {
      const updated = await taskApi.update(taskId, changes);
      setTasks((current) =>
        sortTasks(current.map((item) => (item.id === taskId ? updated : item))),
      );
      setNotice("Task changes saved locally.");
      return true;
    } catch (updateError) {
      setError(messageFor(updateError, "Aria could not save those changes."));
      return false;
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(taskId);
        return next;
      });
    }
  }

  async function deleteTask(taskId: number): Promise<boolean> {
    setDeletingIds((current) => new Set(current).add(taskId));
    setError("");
    setNotice("");
    try {
      await taskApi.remove(taskId);
      setTasks((current) => current.filter((task) => task.id !== taskId));
      setNotice("Task deleted from this local workspace.");
      return true;
    } catch (deleteError) {
      setError(messageFor(deleteError, "Aria could not delete that task."));
      return false;
    } finally {
      setDeletingIds((current) => {
        const next = new Set(current);
        next.delete(taskId);
        return next;
      });
    }
  }

  function clearFeedback() {
    setError("");
    setNotice("");
  }

  return {
    tasks,
    loading,
    saving,
    updatingIds,
    deletingIds,
    error,
    notice,
    retry: load,
    createTask,
    toggleCompleted,
    updateTask,
    deleteTask,
    clearFeedback,
  };
}

