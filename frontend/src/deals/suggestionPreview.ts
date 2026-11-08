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
  return `Add the missing details: ${labels.join(", ")}. Suggested format: “Order of [item], [quantity] [unit] at [currency code] [price] each, ship to [city or port] by YYYY-MM-DD.”`;
}

export function missingRequiredTradeFields(
  facts: DealFact[],
  serverMissingFields: RequiredTradeField[] | null,
): RequiredTradeField[] {
  return REQUIRED_TRADE_FIELDS
    .filter(({ key }) => {
      if (serverMissingFields !== null) return serverMissingFields.includes(key);
      const matchingFacts = facts.filter((fact) => requiredTradeField(fact.field) === key);
      if (matchingFacts.length > 0) {
        return !matchingFacts.some((fact) => fact.status === "EXTRACTED" || fact.status === "CONFIRMED");
      }
      return true;
    })
    .map(({ key }) => key);
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
  currency: string;
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

export interface SharedTermDrift {
  field: RequiredTradeField;
  label: string;
  values: Array<{ value: string; facts: DealFact[] }>;
}

function normalizedDecimal(value: string): string {
  const normalized = value.trim();
  if (!/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(normalized)) return normalized.toLocaleLowerCase();
  return normalized.includes(".")
    ? normalized.replace(/0+$/, "").replace(/\.$/, "")
    : normalized;
}

/** Compare only AI/user-reviewed facts that both parties explicitly shared. */
export function findSharedTermDrift(facts: DealFact[]): SharedTermDrift[] {
  const labels = new Map<RequiredTradeField, string>([
    ["item_description", "Product"], ["quantity", "Quantity"], ["unit", "Unit"],
    ["unit_price", "Unit price"], ["delivery_destination", "Delivery destination"],
    ["delivery_date", "Delivery date"],
  ]);
  const groups = new Map<RequiredTradeField, Map<string, DealFact[]>>();
  for (const fact of facts) {
    if (fact.visibility !== "SHAREABLE" || !["EXTRACTED", "CONFIRMED"].includes(fact.status)) continue;
    const field = requiredTradeField(fact.field);
    if (!field) continue;
    const value = field === "unit_price"
      ? `${normalizedDecimal(fact.typed_value)} ${fact.currency_or_unit ?? ""}`.trim().toUpperCase()
      : field === "quantity" && fact.currency_or_unit
        ? `${normalizedDecimal(fact.typed_value)} ${fact.currency_or_unit.trim().toLocaleLowerCase()}`
        : field === "quantity"
          ? normalizedDecimal(fact.typed_value)
          : fact.typed_value.trim().toLocaleLowerCase();
    const values = groups.get(field) ?? new Map<string, DealFact[]>();
    values.set(value, [...(values.get(value) ?? []), fact]);
    groups.set(field, values);
  }
  return [...groups.entries()]
    .filter(([, values]) => values.size > 1)
    .map(([field, values]) => ({
      field,
      label: labels.get(field) ?? field,
      values: [...values.values()].map((matches) => {
        const fact = matches[0];
        const value = field === "unit_price"
          ? `${normalizedDecimal(fact.typed_value)} ${fact.currency_or_unit?.trim().toUpperCase() ?? ""}`.trim()
          : field === "quantity" && fact.currency_or_unit
            ? `${normalizedDecimal(fact.typed_value)} ${fact.currency_or_unit.trim().toLocaleLowerCase()}`
            : fact.typed_value;
        return { value, facts: matches };
      }),
    }));
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
