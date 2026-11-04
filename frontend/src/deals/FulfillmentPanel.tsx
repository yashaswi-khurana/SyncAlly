import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, getDealFulfillment, recordDealFulfillment } from "../api/client";
import type { FulfillmentSnapshot, FulfillmentStage } from "../api/types";

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
  const [saving, setSaving] = useState(false);
  const [writeError, setWriteError] = useState("");
  const idempotency = useRef<{ request: string; key: string } | null>(null);
  const requestKey = `${dealId}:${reloadToken}:${reloadCount}`;

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void getDealFulfillment(dealId, controller.signal).then(
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
  }, [dealId, reloadCount, reloadToken, requestKey]);

  const state = loaded?.key === requestKey ? loaded.state : { status: "loading" as const };
  const snapshot = state.status === "ready" ? state.snapshot : null;
  const isSeller = selectedOrganizationId === sellerOrganizationId;
  const isBuyer = selectedOrganizationId === buyerOrganizationId;
  const allowedStages: readonly FulfillmentStage[] = isSeller ? ["SHIPPED"] : isBuyer ? ["OBSERVED", "CONFIRMED"] : [];
  const currentStage = allowedStages.includes(stage) ? stage : allowedStages[0] ?? stage;

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
    ]);
    if (idempotency.current?.request !== request) {
      idempotency.current = { request, key: crypto.randomUUID() };
    }
    const idempotencyKey = idempotency.current.key;
    setSaving(true);
    setWriteError("");
    try {
      await recordDealFulfillment(dealId, {
        agreement_version_id: snapshot.agreement_version_id,
        terms_hash: snapshot.terms_hash,
        obligation_id: snapshot.obligation_id,
        organization_id: selectedOrganizationId,
        event_type: currentStage,
        quantity,
        expected_version: snapshot.fulfillment_version,
        idempotency_key: idempotencyKey,
      });
      idempotency.current = null;
      setQuantity("");
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

  function refresh() {
    setWriteError("");
    setReloadCount((count) => count + 1);
  }

  return (
    <section className="card payment-status fulfillment-panel" aria-labelledby="fulfillment-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Participant delivery record</span>
          <h2 id="fulfillment-heading">Fulfillment</h2>
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
        <p role="status">A committed agreement is required before delivery facts can be recorded.</p>
      ) : null}
      {snapshot?.state === "STALE" ? (
        <>
          <div className="payment-status__message" role="status">
            <p>Saved delivery facts belong to an earlier agreement version. Review the current committed agreement before continuing.</p>
          </div>
          <div className="payment-status__list" aria-label="Delivery history">
            {snapshot.events.length ? snapshot.events.map((item) => (
              <article className="payment-status__item" key={item.id}>
                <div className="payment-status__summary">
                  <h3>{item.event_type.toLowerCase()} · {item.quantity} {item.unit}</h3>
                  <span>Earlier terms</span>
                </div>
                <p>{new Date(item.recorded_at).toLocaleString()} · reported by a deal participant</p>
              </article>
            )) : <p>No delivery facts recorded yet.</p>}
          </div>
        </>
      ) : null}
      {snapshot && snapshot.state !== "PENDING" && snapshot.state !== "STALE" ? (
        <>
          <dl className="fulfillment-panel__terms">
            <div><dt>Planned</dt><dd>{snapshot.planned_quantity} {snapshot.unit}</dd></div>
            <div><dt>Destination</dt><dd>{snapshot.destination}</dd></div>
            <div><dt>Target date</dt><dd>{snapshot.target_date ?? "Not specified"}</dd></div>
            <div><dt>Shipped</dt><dd>{snapshot.shipped_quantity} {snapshot.unit}</dd></div>
            <div><dt>Observed</dt><dd>{snapshot.observed_quantity} {snapshot.unit}</dd></div>
            <div><dt>Confirmed</dt><dd>{snapshot.confirmed_quantity} {snapshot.unit}</dd></div>
          </dl>
          {snapshot.deal_completed ? (
            <p role="status">Delivery and required payments are reconciled. The deal is complete.</p>
          ) : (
            <p className="payment-status__footnote">
              Completion requires the full agreed quantity to be confirmed and all required payments to be reconciled.
            </p>
          )}
          {allowedStages.length > 0 ? (
            <form className="fulfillment-panel__form" onSubmit={submit}>
              {allowedStages.length > 1 ? (
                <label>
                  Delivery fact
                  <select value={currentStage} onChange={(event) => setStage(event.target.value as FulfillmentStage)} disabled={saving}>
                    <option value="OBSERVED">Observed by buyer</option>
                    <option value="CONFIRMED">Confirmed by buyer</option>
                  </select>
                </label>
              ) : null}
              <label>
                Quantity ({snapshot.unit})
                <input
                  inputMode="decimal"
                  value={quantity}
                  onChange={(event) => setQuantity(event.target.value)}
                  placeholder="Enter an exact quantity"
                  required
                  disabled={saving}
                />
              </label>
              <button type="submit" className="button" disabled={saving || !quantity.trim()}>
                {saving ? "Saving…" : `Record ${currentStage.toLowerCase()}`}
              </button>
            </form>
          ) : null}
          {!selectedOrganizationId ? <p>Select a buyer or seller organization to record a delivery fact.</p> : null}
          {selectedOrganizationId && !isBuyer && !isSeller ? <p>Select a deal party organization to record a delivery fact.</p> : null}
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
                  <h3>{item.event_type.toLowerCase()} · {item.quantity} {item.unit}</h3>
                  <span>{item.agreement_version_id === snapshot.agreement_version_id ? "Current terms" : "Earlier terms"}</span>
                </div>
                <p>{new Date(item.recorded_at).toLocaleString()} · reported by a deal participant</p>
              </article>
            )) : <p>No delivery facts recorded yet.</p>}
          </div>
        </>
      ) : null}
    </section>
  );
}
