export type AssistantStatus =
  | "succeeded"
  | "proposed"
  | "requires_confirmation"
  | "needs_clarification"
  | "rejected"
  | "failed";

export interface AssistantEvidence {
  source_type: string;
  reference_id: string;
  summary: string;
  observed_at: string | null;
}

export interface AssistantReasoning {
  code: string;
  summary: string;
  details: Record<string, unknown>;
}

export interface AssistantChange {
  field: string;
  before: unknown;
  after: unknown;
}

export interface AssistantProposal {
  proposal_id: string;
  action: string;
  summary: string;
  changes: AssistantChange[];
}

export interface AssistantConfirmation {
  confirmation_id: string;
  proposal_id: string;
  token: string;
  expires_at: string;
  reason: string;
}

export interface AssistantClarification {
  field: string;
  question: string;
  reason: string;
  allow_free_text: boolean;
}

export interface AssistantResult {
  command_name: string;
  correlation_id: string;
  status: AssistantStatus;
  data: Record<string, unknown>;
  warnings: Array<{ code: string; message: string; severity: string }>;
  evidence: AssistantEvidence[];
  reasoning: AssistantReasoning[];
  proposals: AssistantProposal[];
  clarification: AssistantClarification | null;
  confirmation: AssistantConfirmation | null;
  display_summary: string;
  speakable_text: string;
}
