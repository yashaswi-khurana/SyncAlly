import type { Visibility } from "../api/types";

export interface OpeningMessageDraft {
  dealId: string;
  organizationId: string;
  body: string;
  visibility: Visibility;
  idempotencyKey: string | null;
}

export type OpeningMessageDraftInput = Omit<OpeningMessageDraft, "dealId">;
