import { useEffect, useState } from "react";
import { request } from "../../lib/api";

type TesterConsoleProps = {
  taskCount: number;
};

export function TesterConsole({ taskCount }: TesterConsoleProps) {
  const [apiStatus, setApiStatus] = useState("checking");

  useEffect(() => {
    let active = true;
    request<{ status: string }>("/health")
      .then((result) => {
        if (active) setApiStatus(result.status);
      })
      .catch(() => {
        if (active) setApiStatus("offline");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <details className="tester-console">
      <summary>Tester tools</summary>
      <div className="tester-grid">
        <div><span>API</span><strong>{apiStatus}</strong></div>
        <div><span>Loaded tasks</span><strong>{taskCount}</strong></div>
        <div><span>Time zone</span><strong>{Intl.DateTimeFormat().resolvedOptions().timeZone}</strong></div>
        <div><span>Data mode</span><strong>local SQLite</strong></div>
      </div>
      <p>
        Development-only diagnostics. This panel is hidden unless the tester build flag is enabled.
      </p>
    </details>
  );
}
