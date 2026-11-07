import { useId } from "react";

import { paymentTimingLabel } from "../api/types";
import type { NegotiationProposal } from "../api/types";

type Terms = NegotiationProposal["terms"];
type Field = readonly [label: string, value: string | null, identity?: string];
type Entry = { id?: string; label: string; fields: Field[] };
type Change = { before?: Entry; after?: Entry };

function money(value: { amount: string; currency: string }) {
  return value.amount + " " + value.currency;
}

function normalizeLocation(value: string) {
  return value.toLowerCase();
}

function allocations<T>(
  values: T[],
  describe: (value: T) => string,
  identity: (value: T) => string[],
): Field {
  return [
    "Allocations",
    values.length ? values.map(describe).join("; ") : null,
    JSON.stringify(values.map((value) => JSON.stringify(identity(value))).sort()),
  ];
}

function entries(terms: Terms) {
  const lineItems = terms.line_items ?? [];
  const shipmentsTerms = terms.shipments ?? [];
  const paymentTerms = terms.payment_terms ?? [];
  const obligations = new Map<string, { label: string; comparisonKey: string }>();
  const items = lineItems.map((item, index) => {
    const label = "Item " + (index + 1) + ": " + item.description;
    if (item.id) obligations.set(item.id, {
      label,
      comparisonKey: JSON.stringify([item.description.toLowerCase(), item.sku?.toLowerCase() ?? null]),
    });
    return { id: item.id, label, fields: [
      ["Description", item.description],
      ["Quantity", item.quantity + " " + item.unit],
      ["SKU", item.sku],
      ["Unit price", money(item.unit_price)],
    ] satisfies Field[] };
  });
  const shipments = shipmentsTerms.map((shipment, index) => {
    const label = "Shipment " + (index + 1) + " to " + shipment.destination;
    if (shipment.id) obligations.set(shipment.id, {
      label,
      comparisonKey: JSON.stringify([
        normalizeLocation(shipment.destination), shipment.target_date, shipment.quantity,
      ]),
    });
    return { id: shipment.id, label, fields: [
      ["Destination", shipment.destination, normalizeLocation(shipment.destination)],
      ["Delivery date", shipment.target_date],
      ["Quantity", shipment.quantity],
      allocations(
        shipment.allocations ?? [],
        (value) => value.quantity + " " + value.unit + " for " + (obligations.get(value.line_item_id)?.label ?? "a line item"),
        (value) => [obligations.get(value.line_item_id)?.comparisonKey ?? value.line_item_id, value.quantity, value.unit],
      ),
    ] satisfies Field[] };
  });
  const payments = paymentTerms.map((payment, index) => ({
    id: payment.id,
    label: "Payment " + (index + 1) + ": " + paymentTimingLabel(payment.trigger),
    fields: [
      ["Amount", money(payment.amount)],
      ["Timing", paymentTimingLabel(payment.trigger), payment.trigger],
      ["Due condition", payment.due_condition],
      allocations(
        payment.allocations ?? [],
        (value) => money(value.amount) + " for " + (obligations.get(value.obligation_id)?.label ?? "a trade obligation"),
        (value) => [obligations.get(value.obligation_id)?.comparisonKey ?? value.obligation_id, value.amount.amount, value.amount.currency],
      ),
    ] satisfies Field[],
  }));
  const trade = { label: "Other trade terms", fields: [
    ["Delivery location", terms.delivery_location, normalizeLocation(terms.delivery_location)],
    ["Incoterm", terms.incoterm],
    ["Cancellation terms", terms.cancellation_terms],
  ] satisfies Field[] };
  return { items, shipments, payments, trade };
}

function fieldValue(field: Field) {
  return field[2] ?? (field[1] || null);
}

function compareEntries(before: Entry, after: Entry): Change[] {
  const changed = after.fields.map((field, index) => fieldValue(field) !== fieldValue(before.fields[index]));
  if (!changed.some(Boolean)) return [];
  return [{
    before: { ...before, fields: before.fields.filter((_, index) => changed[index]) },
    after: { ...after, fields: after.fields.filter((_, index) => changed[index]) },
  }];
}

function sameTerms(before: Entry, after: Entry) {
  return after.fields.every((field, index) => fieldValue(field) === fieldValue(before.fields[index]));
}

function compareCollection(before: Entry[], after: Entry[]): Change[] {
  // A legacy singleton can be compared with the only entry of its kind in the next round.
  if (before.length === 1 && after.length === 1 && (!before[0].id || !after[0].id)) {
    return compareEntries(before[0], after[0]);
  }

  const unmatched = [...before];
  const changes = after.flatMap((entry): Change[] => {
    const byId = entry.id ? unmatched.findIndex((previous) => previous.id === entry.id) : -1;
    const byTerms = byId < 0 ? unmatched.findIndex((previous) => sameTerms(previous, entry)) : -1;
    // ponytail: pair remaining ID-less legacy entries by order; schema v1 has no stable identity to disambiguate them.
    const byLegacyPosition = byId < 0 && byTerms < 0 && !entry.id
      ? unmatched.findIndex((previous) => !previous.id)
      : -1;
    const match = byId >= 0 ? byId : byTerms >= 0 ? byTerms : byLegacyPosition;
    if (match < 0) return [{ after: entry }];
    const [previous] = unmatched.splice(match, 1);
    return compareEntries(previous, entry);
  });
  return [...changes, ...unmatched.map((entry) => ({ before: entry }))];
}

function ProposalValues({ round, entry }: { round: string; entry: Entry | undefined }) {
  return <div>
    <strong>{round}</strong>
    {entry ? <dl>
      {entry.fields.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value || "Not specified"}</dd></div>)}
    </dl> : <p className="muted">Not included</p>}
  </div>;
}

export default function ProposalComparison({ latest, proposals }: {
  latest: NegotiationProposal;
  proposals: NegotiationProposal[];
}) {
  const headingId = useId();
  const previous = proposals.find((proposal) => proposal.id === latest.based_on_proposal_id && proposal.id !== latest.id);
  const before = previous ? entries(previous.terms) : null;
  const after = before ? entries(latest.terms) : null;
  const changes = before && after ? [
    ...compareCollection(before.items, after.items),
    ...compareCollection(before.shipments, after.shipments),
    ...compareCollection(before.payments, after.payments),
    ...compareEntries(before.trade, after.trade),
  ] : [];

  return <section className="proposal-comparison" aria-labelledby={headingId}>
    <h4 id={headingId}>Changes from the previous proposal</h4>
    {!previous ? <p className="muted">{latest.based_on_proposal_id
      ? "The previous proposal is unavailable for comparison."
      : "This proposal has no linked previous round to compare."}</p> : changes.length ? (
      <ul role="list">
        {changes.map(({ before, after }, index) => <li key={index}>
          <h5>{(after ?? before)?.label} <span className="muted">· {before && after ? "Changed" : after ? "Added" : "Removed"}</span></h5>
          <div className="proposal-comparison__values">
            <ProposalValues round={"Previous · Round " + previous.proposal_number} entry={before} />
            <ProposalValues round={"Current · Round " + latest.proposal_number} entry={after} />
          </div>
        </li>)}
      </ul>
    ) : <p>No commercial terms changed since round {previous.proposal_number}.</p>}
  </section>;
}
