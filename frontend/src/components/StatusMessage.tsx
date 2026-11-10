type StatusMessageProps = {
  message: string;
  onRetry?: () => void;
  tone?: "error" | "success";
};

export function StatusMessage({ message, onRetry, tone = "error" }: StatusMessageProps) {
  return (
    <div className={`status-message ${tone}`} role={tone === "error" ? "alert" : "status"}>
      <p>{message}</p>
      {onRetry && (
        <button className="secondary" type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

