import type { KeyboardEvent } from "react";

const focusableSelector = [
  "button:not(:disabled)",
  "input:not(:disabled)",
  "select:not(:disabled)",
  "textarea:not(:disabled)",
  "[href]",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function handleDialogKeyboard(
  event: KeyboardEvent<HTMLElement>,
  busy: boolean,
  onEscape: () => void,
) {
  if (event.key === "Escape" && !busy) {
    event.preventDefault();
    onEscape();
    return;
  }

  if (event.key !== "Tab") return;

  const focusable = Array.from(
    event.currentTarget.querySelectorAll<HTMLElement>(focusableSelector),
  );
  if (focusable.length === 0) return;

  const first = focusable[0];
  const last = focusable.at(-1)!;
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

