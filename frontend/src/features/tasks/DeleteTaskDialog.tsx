import { useEffect, useRef } from "react";
import { handleDialogKeyboard } from "../../components/dialogKeyboard";
import type { Task } from "./types";

type DeleteTaskDialogProps = {
  task: Task;
  deleting: boolean;
  error?: string;
  onCancel: () => void;
  onConfirm: () => Promise<boolean>;
};

export function DeleteTaskDialog({
  task,
  deleting,
  error,
  onCancel,
  onConfirm,
}: DeleteTaskDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const titleId = `delete-task-${task.id}-title`;

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  return (
    <div
      className="dialog-backdrop"
      onKeyDown={(event) => handleDialogKeyboard(event, deleting, onCancel)}
    >
      <section
        className="dialog-card confirm-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={`${titleId}-description`}
      >
        <p className="eyebrow">Confirm deletion</p>
        <h2 id={titleId}>Delete “{task.title}”?</h2>
        <p id={`${titleId}-description`}>
          This removes the task from this local workspace. This action cannot be undone.
        </p>
        {error && (
          <p className="dialog-error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-actions">
          <button
            ref={cancelRef}
            className="secondary"
            type="button"
            onClick={onCancel}
            disabled={deleting}
          >
            Keep task
          </button>
          <button
            className="danger"
            type="button"
            onClick={() => void onConfirm()}
            disabled={deleting}
          >
            {deleting ? "Deleting locally…" : "Delete task"}
          </button>
        </div>
      </section>
    </div>
  );
}

