import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, PROFILE_CHANGED_EVENT } from "../../lib/api";
import { assistantApi } from "./api";
import type { AssistantResult } from "./types";

interface ConversationItem {
  id: string;
  request: string;
  result?: AssistantResult;
  error?: string;
}

interface AssistantWorkspaceProps {
  onTaskCreated: () => void | Promise<void>;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError && error.detail) return error.detail;
  return "Aria could not process that request. The local API may be unavailable.";
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not set";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
}

export function AssistantWorkspace({ onTaskCreated }: AssistantWorkspaceProps) {
  const [text, setText] = useState("");
  const [items, setItems] = useState<ConversationItem[]>([]);
  const [sending, setSending] = useState(false);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    function resetConversation() {
      setItems([]);
      setText("");
    }
    window.addEventListener(PROFILE_CHANGED_EVENT, resetConversation);
    return () => window.removeEventListener(PROFILE_CHANGED_EVENT, resetConversation);
  }, []);

  async function send(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const request = text.trim();
    if (!request || sending) return;
    const id = crypto.randomUUID();
    setText("");
    setSending(true);
    setItems((current) => [...current, { id, request }]);
    try {
      const result = await assistantApi.send(request);
      setItems((current) =>
        current.map((item) => (item.id === id ? { ...item, result } : item)),
      );
    } catch (error) {
      setItems((current) =>
        current.map((item) =>
          item.id === id ? { ...item, error: errorMessage(error) } : item,
        ),
      );
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  async function confirm(itemId: string, result: AssistantResult) {
    if (!result.confirmation || confirmingId) return;
    setConfirmingId(result.confirmation.confirmation_id);
    try {
      const completed = await assistantApi.confirm(result.confirmation);
      setItems((current) =>
        current.map((item) =>
          item.id === itemId ? { ...item, result: completed, error: undefined } : item,
        ),
      );
      if (completed.command_name === "tasks.create" && completed.status === "succeeded") {
        await onTaskCreated();
      }
    } catch (error) {
      setItems((current) =>
        current.map((item) =>
          item.id === itemId ? { ...item, error: errorMessage(error) } : item,
        ),
      );
    } finally {
      setConfirmingId(null);
    }
  }

  return (
    <section className="panel assistant-workspace" aria-labelledby="assistant-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Typed assistant</p>
          <h2 id="assistant-title">Plan with Aria</h2>
        </div>
        <span className="assistant-local-badge">Offline demo</span>
      </div>

      <div className="assistant-conversation" aria-live="polite">
        {items.length === 0 && (
          <div className="assistant-intro">
            <strong>Try a real local command.</strong>
            <span>Use “show my tasks” or “add task: Review the fictional brief”.</span>
            <span>Aria previews saved changes and waits for your confirmation.</span>
          </div>
        )}
        {items.map((item) => (
          <article className="assistant-exchange" key={item.id}>
            <p className="assistant-user"><span>You</span>{item.request}</p>
            {!item.result && !item.error && <p className="assistant-thinking">Aria is checking…</p>}
            {item.result && (
              <div className="assistant-result">
                <div className="assistant-result-heading">
                  <span>Aria</span>
                  <small>{item.result.status.replaceAll("_", " ")}</small>
                </div>
                <p>{item.result.display_summary}</p>

                {item.result.clarification && (
                  <div className="assistant-clarification">
                    <strong>{item.result.clarification.question}</strong>
                    <span>{item.result.clarification.reason}</span>
                  </div>
                )}

                {item.result.proposals.map((proposal) => (
                  <div className="assistant-proposal" key={proposal.proposal_id}>
                    <strong>Proposed change</strong>
                    <p>{proposal.summary}</p>
                    <dl>
                      {proposal.changes.map((change) => (
                        <div key={change.field}>
                          <dt>{change.field}</dt>
                          <dd>{formatValue(change.after)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                ))}

                {item.result.confirmation && (
                  <div className="assistant-confirmation">
                    <p>{item.result.confirmation.reason}</p>
                    <button
                      className="primary"
                      type="button"
                      disabled={confirmingId !== null}
                      onClick={() => confirm(item.id, item.result!)}
                    >
                      {confirmingId === item.result.confirmation.confirmation_id
                        ? "Confirming…"
                        : "Confirm and save"}
                    </button>
                  </div>
                )}

                {(item.result.evidence.length > 0 || item.result.reasoning.length > 0) && (
                  <details className="assistant-details">
                    <summary>Evidence and reasoning</summary>
                    {item.result.evidence.map((evidence) => (
                      <p key={`${evidence.source_type}-${evidence.reference_id}`}>
                        <strong>Evidence:</strong> {evidence.summary}
                      </p>
                    ))}
                    {item.result.reasoning.map((reason) => (
                      <p key={reason.code}><strong>Reason:</strong> {reason.summary}</p>
                    ))}
                  </details>
                )}
              </div>
            )}
            {item.error && <p className="assistant-error" role="alert">{item.error}</p>}
          </article>
        ))}
      </div>

      <form className="assistant-composer" onSubmit={send}>
        <label htmlFor="assistant-request">Ask Aria</label>
        <textarea
          id="assistant-request"
          ref={inputRef}
          value={text}
          rows={2}
          maxLength={2_000}
          placeholder="Show my tasks"
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
          }}
        />
        <button className="primary" type="submit" disabled={sending || !text.trim()}>
          {sending ? "Sending…" : "Send request"}
        </button>
      </form>
    </section>
  );
}
