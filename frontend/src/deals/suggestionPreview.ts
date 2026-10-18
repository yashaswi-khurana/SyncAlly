import type { DealFact, FactReviewAction, ProposalSuggestion } from "../api/types";

export interface FactSuggestionDraft {
  fact: DealFact;
  field: string;
  value: string;
  currencyOrUnit: string | null;
  pending: boolean;
  error: string;
}

export interface ProposalSuggestionDraft {
  description: string;
  quantity: string;
  unit: string;
  unitPrice: string;
  currency: "USD";
  deliveryDestination: string;
  deliveryDate: string;
}

export function toFactSuggestionDraft(fact: DealFact): FactSuggestionDraft {
  return {
    fact,
    field: fact.field,
    value: fact.typed_value,
    currencyOrUnit: fact.currency_or_unit,
    pending: false,
    error: "",
  };
}

export function toProposalDraft(proposal: ProposalSuggestion): ProposalSuggestionDraft {
  return {
    description: proposal.description,
    quantity: proposal.quantity,
    unit: proposal.unit,
    unitPrice: proposal.unit_price,
    currency: proposal.currency,
    deliveryDestination: proposal.delivery_destination,
    deliveryDate: proposal.delivery_date ?? "",
  };
}

export function reviewActionLabel(action: FactReviewAction): string {
  switch (action) {
    case "confirm":
      return "Confirm";
    case "reject":
      return "Reject";
    case "clarify":
      return "Ask for clarification";
  }
}
