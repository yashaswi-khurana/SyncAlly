import { describe, expect, it } from "vitest";

import type { DealFact } from "../api/types";
import { conversationTermMismatches, savedTermsFromTrade } from "./suggestionPreview";

function fact(overrides: Partial<DealFact>): DealFact {
  return {
    id: "fact-1",
    deal_id: "deal-1",
    owner_organization_id: "buyer",
    field: "item_description",
    typed_value: "Table Tennis ball",
    currency_or_unit: null,
    kind: "INFORMATIONAL",
    status: "CONFIRMED",
    visibility: "PRIVATE",
    source_message_id: "message-1",
    source_span: "Table Tennis ball",
    confirmed_by: "user-1",
    confirmed_at: "2026-11-11T21:00:00Z",
    version: 1,
    created_at: "2026-11-11T20:49:08Z",
    ...overrides,
  };
}

describe("conversationTermMismatches", () => {
  it("flags a committed gasifier agreement against a table-tennis conversation", () => {
    const facts = [
      fact({ id: "item", field: "item_description", typed_value: "Table Tennis ball", status: "CONFIRMED" }),
      fact({ id: "qty", field: "quantity", typed_value: "20", status: "EXTRACTED", confirmed_by: null, confirmed_at: null }),
      fact({
        id: "price", field: "unit_price", typed_value: "2", currency_or_unit: "Dollar",
        status: "CONFIRMED", visibility: "SHAREABLE",
      }),
      fact({
        id: "place", field: "delivery_destination", typed_value: "123, Park Avenue, Torronto",
        status: "EXTRACTED", confirmed_by: null, confirmed_at: null,
      }),
      fact({
        id: "when", field: "delivery_date", typed_value: "Tommorow,12 PM",
        status: "CONFIRMED", visibility: "SHAREABLE",
      }),
    ];
    const mismatches = conversationTermMismatches(facts, savedTermsFromTrade({
      line_items: [{
        description: "Stainless Gasifiers",
        quantity: "7",
        unit: "units",
        unit_price: { amount: "120000", currency: "INR" },
      }],
      shipments: [{ destination: "Mohali", target_date: "2026-11-21" }],
      delivery_location: "Best tech business tour",
    }));
    expect(mismatches.map((item) => item.field)).toEqual([
      "item_description",
      "quantity",
      "unit_price",
      "delivery_destination",
      "delivery_date",
    ]);
    expect(mismatches[0]).toMatchObject({
      conversation: "Table Tennis ball",
      saved: "Stainless Gasifiers",
    });
  });

  it("does not flag matching conversation facts", () => {
    const facts = [
      fact({ typed_value: "Stainless Gasifiers" }),
      fact({ id: "qty", field: "quantity", typed_value: "7", currency_or_unit: "units" }),
    ];
    expect(conversationTermMismatches(facts, {
      description: "Stainless Gasifiers",
      quantity: "7",
      unit: "units",
    })).toEqual([]);
  });
});
