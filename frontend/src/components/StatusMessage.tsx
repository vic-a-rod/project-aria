type StatusMessageProps = {
  message: string;
  onRetry?: () => void;
};

export function StatusMessage({ message, onRetry }: StatusMessageProps) {
  return (
    <div className="error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button className="secondary" type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

