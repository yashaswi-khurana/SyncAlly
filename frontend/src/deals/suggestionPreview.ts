import type { DealFact, FactReviewAction, ProposalSuggestion } from "../api/types";

export const REQUIRED_TRADE_FIELDS = [
  { key: "item_description", label: "Item Description" },
  { key: "quantity", label: "Quantity" },
  { key: "unit", label: "Unit" },
  { key: "unit_price", label: "Unit Price" },
  { key: "delivery_destination", label: "Delivery Destination" },
  { key: "delivery_date", label: "Delivery Date" },
] as const;

export type RequiredTradeField = (typeof REQUIRED_TRADE_FIELDS)[number]["key"];

const REQUIRED_FIELD_ALIASES: Record<string, RequiredTradeField> = {
  description: "item_description",
  item: "item_description",
  itemdescription: "item_description",
  item_description: "item_description",
  quantity: "quantity",
  unit: "unit",
  unitprice: "unit_price",
  unit_price: "unit_price",
  price: "unit_price",
  deliverydestination: "delivery_destination",
  delivery_destination: "delivery_destination",
  destination: "delivery_destination",
  deliverydate: "delivery_date",
  delivery_date: "delivery_date",
};

export function requiredTradeField(field: string): RequiredTradeField | null {
  const normalized = field.trim().toLowerCase().replaceAll(/[^a-z0-9]+/g, "_");
  const compact = normalized.replaceAll("_", "");
  return REQUIRED_FIELD_ALIASES[normalized] ?? REQUIRED_FIELD_ALIASES[compact] ?? null;
}

export function guidanceForMissingTradeFields(fields: RequiredTradeField[]): string {
  if (fields.length === 0) {
    return "All required trade details were found. Review each fact before using a draft.";
  }
  const labels = fields.map((field) =>
    REQUIRED_TRADE_FIELDS.find((required) => required.key === field)?.label.toLowerCase() ?? field,
  );
  return `Add the missing details: ${labels.join(", ")}. Suggested format: “Order of [item], [quantity] [unit] at USD [price] each, ship to [city or port] by YYYY-MM-DD.”`;
}

export interface FactSuggestionDraft {
  fact: DealFact;
  field: string;
  value: string;
  currencyOrUnit: string | null;
  pending: boolean;
  error: string;
}

export interface ProposalSuggestionDraft {
  schemaVersion: number;
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
    schemaVersion: proposal.schema_version,
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
