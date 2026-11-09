import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, getDealFulfillment, raiseDealCase, recordDealFulfillment } from "../api/client";
import type { FulfillmentEvent, FulfillmentSnapshot, FulfillmentStage } from "../api/types";

type FulfillmentState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "revoked"; snapshot: FulfillmentSnapshot | null }
  | { status: "ready"; snapshot: FulfillmentSnapshot };

interface FulfillmentPanelProps {
  dealId: string;
  buyerOrganizationId: string;
  sellerOrganizationId: string;
  selectedOrganizationId: string;
  reloadToken?: number;
  onChanged?: () => void;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Unable to load delivery records.";
}

function stageLabel(stage: FulfillmentStage): string {
  switch (stage) {
    case "SHIPPED": return "Seller reported shipment";
    case "OBSERVED": return "Buyer recorded received quantity";
    case "CONFIRMED": return "Buyer confirmed received quantity";
  }
}

function eventReporter(organizationId: string, buyerOrganizationId: string, sellerOrganizationId: string): string {
  if (organizationId === buyerOrganizationId) return "Reported by buyer";
  if (organizationId === sellerOrganizationId) return "Reported by seller";
  return "Reported by a deal participant";
}

function shipmentDetails(event: FulfillmentEvent): string {
  return [
    event.carrier ?? "Carrier not recorded",
    event.tracking_number ? `Tracking ${event.tracking_number}` : "No tracking number",
    event.dispatch_date ? `Dispatched ${event.dispatch_date}` : null,
    event.expected_delivery_date ? `Expected ${event.expected_delivery_date}` : null,
  ].filter(Boolean).join(" · ");
}

function today(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

type DeliveryExceptionType = "SHORTAGE" | "DAMAGE" | "OTHER";

const DELIVERY_EXCEPTION_LABELS: Record<DeliveryExceptionType, string> = {
  SHORTAGE: "Shortage",
  DAMAGE: "Damage",
  OTHER: "Other delivery issue",
};

export default function FulfillmentPanel({
  dealId,
  buyerOrganizationId,
  sellerOrganizationId,
  selectedOrganizationId,
  reloadToken = 0,
  onChanged,
}: FulfillmentPanelProps) {
  const [loaded, setLoaded] = useState<{ key: string; state: FulfillmentState } | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  const [stage, setStage] = useState<FulfillmentStage>("SHIPPED");
  const [quantity, setQuantity] = useState("");
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");
  const [dispatchDate, setDispatchDate] = useState(today);
  const [expectedDeliveryDate, setExpectedDeliveryDate] = useState("");
  const [showExceptionForm, setShowExceptionForm] = useState(false);
  const [selectedShipmentId, setSelectedShipmentId] = useState("");
  const [exceptionType, setExceptionType] = useState<DeliveryExceptionType>("SHORTAGE");
  const [exceptionQuantity, setExceptionQuantity] = useState("");
  const [exceptionDetails, setExceptionDetails] = useState("");
  const [savingException, setSavingException] = useState(false);
  const [exceptionError, setExceptionError] = useState("");
  const [saving, setSaving] = useState(false);
  const [writeError, setWriteError] = useState("");
  const idempotency = useRef<{ request: string; key: string } | null>(null);
  const exceptionIdempotency = useRef<{ request: string; key: string } | null>(null);
  const requestKey = `${dealId}:${reloadToken}:${reloadCount}`;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void getDealFulfillment(dealId, selectedOrganizationId, controller.signal).then(
      (snapshot) => {
        if (active) setLoaded({ key: requestKey, state: { status: "ready", snapshot } });
      },
      (error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 403) {
          setLoaded({ key: requestKey, state: { status: "revoked", snapshot: null } });
        } else {
          setLoaded({ key: requestKey, state: { status: "error", message: errorMessage(error) } });
        }
      },
    );
    return () => {
      active = false;
      controller.abort();
    };
  }, [dealId, selectedOrganizationId, reloadCount, reloadToken, requestKey]);

  const state = loaded?.key === requestKey ? loaded.state : { status: "loading" as const };
  const snapshot = state.status === "ready" ? state.snapshot : null;
  const isSeller = selectedOrganizationId === sellerOrganizationId;
  const isBuyer = selectedOrganizationId === buyerOrganizationId;
  const allowedStages: readonly FulfillmentStage[] = isSeller ? ["SHIPPED"] : isBuyer ? ["OBSERVED", "CONFIRMED"] : [];
  const currentStage = allowedStages.includes(stage) ? stage : allowedStages[0] ?? stage;
  const currentShipments = snapshot?.events.filter(
    (item) => item.event_type === "SHIPPED" && item.agreement_version_id === snapshot.agreement_version_id,
  ) ?? [];
  const selectedShipment = currentShipments.find((item) => item.id === selectedShipmentId)
    ?? currentShipments[currentShipments.length - 1];

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !snapshot?.agreement_version_id ||
      !snapshot.terms_hash ||
      !snapshot.obligation_id ||
      !selectedOrganizationId ||
      !allowedStages.includes(currentStage) ||
      saving
    ) return;

    const request = JSON.stringify([
      dealId,
      snapshot.agreement_version_id,
      snapshot.terms_hash,
      snapshot.obligation_id,
      selectedOrganizationId,
      currentStage,
      quantity,
      currentStage === "SHIPPED" ? carrier.trim() : null,
      currentStage === "SHIPPED" ? trackingNumber.trim() : null,
      currentStage === "SHIPPED" ? dispatchDate : null,
      currentStage === "SHIPPED" ? expectedDeliveryDate || null : null,
    ]);
    if (idempotency.current?.request !== request) {
      idempotency.current = { request, key: crypto.randomUUID() };
    }
    const idempotencyKey = idempotency.current.key;
    setSaving(true);
    setWriteError("");
    try {
      const common = {
        agreement_version_id: snapshot.agreement_version_id,
        terms_hash: snapshot.terms_hash,
        obligation_id: snapshot.obligation_id,
        organization_id: selectedOrganizationId,
        quantity,
        expected_version: snapshot.fulfillment_version,
        idempotency_key: idempotencyKey,
      };
      const input = currentStage === "SHIPPED"
        ? {
            ...common,
            event_type: "SHIPPED" as const,
            carrier: carrier.trim(),
            tracking_number: trackingNumber.trim() || null,
            dispatch_date: dispatchDate,
            expected_delivery_date: expectedDeliveryDate || null,
          }
        : { ...common, event_type: currentStage };
      await recordDealFulfillment(dealId, input);
      idempotency.current = null;
      setQuantity("");
      setCarrier("");
      setTrackingNumber("");
      setDispatchDate(today());
      setExpectedDeliveryDate("");
      setReloadCount((count) => count + 1);
      onChanged?.();
    } catch (error: unknown) {
      if (error instanceof ApiError && error.status === 403) {
        setLoaded({ key: requestKey, state: { status: "revoked", snapshot } });
      } else if (error instanceof ApiError && error.status === 409) {
        setWriteError("The committed terms or delivery history changed. Refresh before recording another fact.");
      } else {
        setWriteError(errorMessage(error));
      }
    } finally {
      setSaving(false);
    }
  }

  async function reportException(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      !snapshot?.agreement_version_id ||
      !snapshot.terms_hash ||
      !snapshot.obligation_id ||
      !selectedShipment ||
      selectedOrganizationId !== buyerOrganizationId ||
      savingException
    ) return;

    const affectedQuantity = exceptionQuantity.trim();
    const affectedAmount = Number(affectedQuantity);
    if (affectedQuantity && (!/^\d+(?:\.\d+)?$/.test(affectedQuantity) || !Number.isFinite(affectedAmount) || affectedAmount <= 0)) {
      setExceptionError("Enter a positive affected quantity, or leave it blank.");
      return;
    }
    const details = exceptionDetails.trim();
    if (!details) {
      setExceptionError("Describe what arrived and what is wrong.");
      return;
    }

    const request = JSON.stringify([
      dealId,
      snapshot.agreement_version_id,
      snapshot.terms_hash,
      selectedOrganizationId,
      selectedShipment.id,
      exceptionType,
      affectedQuantity,
      details,
    ]);
    if (exceptionIdempotency.current?.request !== request) {
      exceptionIdempotency.current = { request, key: crypto.randomUUID() };
    }

    setSavingException(true);
    setExceptionError("");
    try {
      await raiseDealCase(dealId, {
        case_type: "DISPUTE",
        case_id: exceptionIdempotency.current.key,
        reason: `Delivery exception: ${DELIVERY_EXCEPTION_LABELS[exceptionType]}`,
        agreement_version_id: snapshot.agreement_version_id,
        agreement_terms_hash: snapshot.terms_hash,
        obligation_references: snapshot.obligation_reference ? [snapshot.obligation_reference] : [],
        delivery_exception: {
          kind: "DELIVERY_EXCEPTION",
          exception_type: exceptionType,
          affected_quantity: affectedQuantity || null,
          unit: selectedShipment.unit,
          fulfillment_event_id: selectedShipment.id,
        },
        evidence_visibility: "MUTUAL_VISIBLE",
        evidence_notes: [
          affectedQuantity ? `Affected quantity: ${affectedQuantity} ${selectedShipment.unit}` : null,
          details,
        ].filter(Boolean).join("\n\n"),
        acting_organization_id: selectedOrganizationId,
      });
      exceptionIdempotency.current = null;
      setShowExceptionForm(false);
      setExceptionQuantity("");
      setExceptionDetails("");
      onChanged?.();
    } catch (error: unknown) {
      setExceptionError(error instanceof ApiError ? error.message : "Unable to report this delivery issue.");
    } finally {
      setSavingException(false);
    }
  }

  function refresh() {
    setWriteError("");
    setReloadCount((count) => count + 1);
  }

  return (
    <section className="card payment-status fulfillment-panel" aria-labelledby="fulfillment-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Delivery progress</span>
          <h2 id="fulfillment-heading">Delivery</h2>
        </div>
        <button type="button" className="button secondary button--compact" onClick={refresh}>
          Refresh status
        </button>
      </div>

      {state.status === "loading" ? <p role="status">Loading delivery records…</p> : null}
      {state.status === "error" ? (
        <div className="payment-status__message" role="alert">
          <p>Delivery records are unavailable. {state.message}</p>
        </div>
      ) : null}
      {state.status === "revoked" ? (
        <div className="payment-status__message" role="alert">
          <p>Your organization membership or fulfillment permission is unavailable. Ask an organization admin to review access.</p>
        </div>
      ) : null}
      {snapshot?.state === "PENDING" ? (
        <p role="status">Delivery updates become available after both parties commit the agreement.</p>
      ) : null}
      {snapshot?.state === "STALE" ? (
        <>
          <div className="payment-status__message" role="status">
            <p>These delivery updates belong to an earlier agreement version. Review the current committed terms before adding another update.</p>
          </div>
          <div className="payment-status__list" aria-label="Delivery history">
            {snapshot.events.length ? snapshot.events.map((item) => (
              <article className="payment-status__item" key={item.id}>
                <div className="payment-status__summary">
                  <h3>{stageLabel(item.event_type)} · {item.quantity} {item.unit}</h3>
                  <span>Earlier terms</span>
                </div>
                <p>{new Date(item.recorded_at).toLocaleString()} · {eventReporter(item.organization_id, buyerOrganizationId, sellerOrganizationId)}</p>
                {item.event_type === "SHIPPED" ? <p>{shipmentDetails(item)}</p> : null}
              </article>
            )) : <p>No delivery facts recorded yet.</p>}
          </div>
        </>
      ) : null}
      {snapshot && snapshot.state !== "PENDING" && snapshot.state !== "STALE" ? (
        <>
          <dl className="fulfillment-panel__terms">
            <div><dt>Agreed quantity</dt><dd>{snapshot.planned_quantity} {snapshot.unit}</dd></div>
            <div><dt>Destination</dt><dd>{snapshot.destination}</dd></div>
            <div><dt>Target date</dt><dd>{snapshot.target_date ?? "Not specified"}</dd></div>
            <div><dt>Seller reported shipped</dt><dd>{snapshot.shipped_quantity} {snapshot.unit}</dd></div>
            <div><dt>Buyer recorded received</dt><dd>{snapshot.observed_quantity} {snapshot.unit}</dd></div>
            <div><dt>Buyer confirmed received</dt><dd>{snapshot.confirmed_quantity} {snapshot.unit}</dd></div>
          </dl>
          {snapshot.deal_completed ? (
            <p role="status">This deal is complete. The agreed delivery quantity is confirmed and required payments are reconciled.</p>
          ) : (
            <p className="payment-status__footnote">
              Completion requires the buyer to confirm the full agreed quantity and all required payments to be reconciled.
            </p>
          )}
          {allowedStages.length > 0 ? (
            <form className="fulfillment-panel__form" onSubmit={submit}>
              {allowedStages.length > 1 ? (
                <label>
                  Delivery update
                  <select value={currentStage} onChange={(event) => setStage(event.target.value as FulfillmentStage)} disabled={saving}>
                    <option value="OBSERVED">Record received quantity</option>
                    <option value="CONFIRMED">Confirm received quantity</option>
                  </select>
                </label>
              ) : null}
              <label>
                Quantity ({snapshot.unit})
                <input
                  inputMode="decimal"
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  placeholder="Enter the quantity"
                  required
                  disabled={saving}
                />
              </label>
              {currentStage === "SHIPPED" ? (
                <>
                  <label>
                    Carrier
                    <input value={carrier} onChange={(event) => setCarrier(event.target.value)} maxLength={120} required disabled={saving} placeholder="Carrier or delivery service" />
                  </label>
                  <label>
                    Tracking number <span className="hint">Optional if the carrier does not provide one</span>
                    <input value={trackingNumber} onChange={(event) => setTrackingNumber(event.target.value)} maxLength={128} disabled={saving} placeholder="Enter tracking number" />
                  </label>
                  <label>
                    Dispatch date
                    <input type="date" value={dispatchDate} onChange={(event) => setDispatchDate(event.target.value)} required disabled={saving} />
                  </label>
                  <label>
                    Expected delivery date <span className="hint">Optional if not yet known</span>
                    <input type="date" value={expectedDeliveryDate} min={dispatchDate || undefined} onChange={(event) => setExpectedDeliveryDate(event.target.value)} disabled={saving} />
                  </label>
                </>
              ) : null}
              <button type="submit" className="button" disabled={saving || !quantity.trim()}>
                {saving ? "Saving…" : currentStage === "SHIPPED" ? "Report shipment" : currentStage === "OBSERVED" ? "Record received quantity" : "Confirm received quantity"}
              </button>
            </form>
          ) : null}
          {!selectedOrganizationId ? <p>Choose the buyer or seller organization above to record a delivery update.</p> : null}
          {selectedOrganizationId && !isBuyer && !isSeller ? <p>Choose an organization that belongs to this deal to record a delivery update.</p> : null}
          {writeError ? (
            <div className="payment-status__message" role="alert">
              <p>{writeError}</p>
              {writeError.includes("Refresh") ? <button type="button" className="button secondary button--compact" onClick={refresh}>Refresh</button> : null}
            </div>
          ) : null}
          <div className="payment-status__list" aria-label="Delivery history">
            {snapshot.events.length ? snapshot.events.map((item) => (
              <article className="payment-status__item" key={item.id}>
                <div className="payment-status__summary">
                  <h3>{stageLabel(item.event_type)} · {item.quantity} {item.unit}</h3>
                  <span>{item.agreement_version_id === snapshot.agreement_version_id ? "Current terms" : "Earlier terms"}</span>
                </div>
                <p>{new Date(item.recorded_at).toLocaleString()} · {eventReporter(item.organization_id, buyerOrganizationId, sellerOrganizationId)}</p>
                {item.event_type === "SHIPPED" ? (
                  <p>{shipmentDetails(item)}</p>
                ) : null}
              </article>
            )) : <p>No delivery facts recorded yet.</p>}
          </div>
          {snapshot.events.some((item) => item.event_type === "SHIPPED" && item.tracking_number) ? (
            <p className="payment-status__footnote">SyncAlly records the seller’s tracking details; check the carrier’s site for live tracking updates.</p>
          ) : null}
          {isBuyer && currentShipments.length > 0 ? (
            <div className="payment-status__message">
              {!showExceptionForm ? (
                <>
                  <p>Received a short or damaged delivery? Report the issue to open a shared dispute case.</p>
                  <button type="button" className="button secondary button--compact" onClick={() => setShowExceptionForm(true)}>
                    Report delivery issue
                  </button>
                </>
              ) : (
                <form className="fulfillment-panel__form" onSubmit={(event) => void reportException(event)}>
                  {currentShipments.length > 1 ? (
                    <label>
                      Shipment
                      <select value={selectedShipment?.id ?? ""} onChange={(event) => setSelectedShipmentId(event.target.value)} disabled={savingException}>
                        {currentShipments.map((item, index) => (
                          <option key={item.id} value={item.id}>
                            Shipment {index + 1} · {item.quantity} {item.unit} · {item.dispatch_date ?? new Date(item.recorded_at).toLocaleDateString()}
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                  {selectedShipment ? <p>{shipmentDetails(selectedShipment)}</p> : null}
                  <label>
                    Issue type
                    <select value={exceptionType} onChange={(event) => setExceptionType(event.target.value as DeliveryExceptionType)} disabled={savingException}>
                      <option value="SHORTAGE">Shortage</option>
                      <option value="DAMAGE">Damage</option>
                      <option value="OTHER">Other issue</option>
                    </select>
                  </label>
                  <label>
                    Affected quantity ({selectedShipment?.unit ?? snapshot.unit}) <span className="hint">Optional</span>
                    <input inputMode="decimal" value={exceptionQuantity} onChange={(event) => setExceptionQuantity(event.target.value)} disabled={savingException} placeholder="Enter affected quantity" />
                  </label>
                  <label>
                    What happened?
                    <textarea value={exceptionDetails} onChange={(event) => setExceptionDetails(event.target.value)} maxLength={2000} required disabled={savingException} rows={3} />
                  </label>
                  <div>
                    <button type="submit" className="button" disabled={savingException || !exceptionDetails.trim()}>
                      {savingException ? "Opening case…" : "Submit delivery issue"}
                    </button>
                    <button type="button" className="button ghost" disabled={savingException} onClick={() => {
                      setShowExceptionForm(false);
                      setExceptionType("SHORTAGE");
                      setExceptionQuantity("");
                      setExceptionDetails("");
                      setExceptionError("");
                    }}>
                      Cancel
                    </button>
                  </div>
                  {exceptionError ? <p role="alert">{exceptionError}</p> : null}
                </form>
              )}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
