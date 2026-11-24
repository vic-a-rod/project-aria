import { request } from "../../lib/api";
import type { AssistantConfirmation, AssistantResult } from "./types";

export const assistantApi = {
  send(text: string): Promise<AssistantResult> {
    return request("/api/assistant/messages", {
      method: "POST",
      body: JSON.stringify({
        text,
        locale: navigator.language || "en-US",
        time_zone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      }),
    });
  },

  confirm(confirmation: AssistantConfirmation): Promise<AssistantResult> {
    return request("/api/assistant/confirmations", {
      method: "POST",
      body: JSON.stringify({
        proposal_id: confirmation.proposal_id,
        confirmation_id: confirmation.confirmation_id,
        token: confirmation.token,
      }),
    });
  },
};
