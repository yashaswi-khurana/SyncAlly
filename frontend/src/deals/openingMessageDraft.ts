export interface OpeningMessageDraft {
  dealId: string;
  organizationId: string;
  body: string;
}

export type OpeningMessageDraftInput = Omit<OpeningMessageDraft, "dealId">;
