import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createDeal, listOrganizations } from "../api/client";
import type { Organization } from "../api/types";
import Reveal from "../ui/Reveal";

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type OrganizationsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "empty" }
  | { status: "ready"; organizations: Organization[] };

interface FieldErrors {
  buyer?: string;
  seller?: string;
}

interface CreateDealPageProps {
  onCreated: (dealId: string) => void;
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

function describeCreateError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    if (caught.status === 403) {
      return "You cannot create a deal for that buyer organization.";
    }
    if (caught.status === 404) {
      return "The buyer or seller organization was not found.";
    }
    return caught.message;
  }
  return "Unable to create the deal. Please try again.";
}

export default function CreateDealPage({ onCreated }: CreateDealPageProps) {
  const [organizationsState, setOrganizationsState] = useState<OrganizationsState>({
    status: "loading",
  });
  const [buyerOrganizationId, setBuyerOrganizationId] = useState("");
  const [sellerOrganizationId, setSellerOrganizationId] = useState(
    import.meta.env.VITE_DEMO_SELLER_ORGANIZATION_ID ?? "",
  );
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const organizations = await listOrganizations();
        if (cancelled) {
          return;
        }
        if (organizations.length === 0) {
          setOrganizationsState({ status: "empty" });
          return;
        }
        setOrganizationsState({ status: "ready", organizations });
        setBuyerOrganizationId((current) => current || organizations[0].id);
      } catch (caught) {
        if (!cancelled) {
          setOrganizationsState({ status: "error", message: describeError(caught) });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadCount]);

  function retryOrganizations() {
    setOrganizationsState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: FieldErrors = {};
    const seller = sellerOrganizationId.trim();
    if (buyerOrganizationId === "") {
      nextErrors.buyer = "Choose the buyer organization.";
    }
    if (seller === "") {
      nextErrors.seller = "Enter the seller organization ID.";
    } else if (!UUID_PATTERN.test(seller)) {
      nextErrors.seller = "Enter a valid organization ID (UUID).";
    } else if (seller.toLowerCase() === buyerOrganizationId.toLowerCase()) {
      nextErrors.seller = "Buyer and seller must be different organizations.";
    }
    setFieldErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      const deal = await createDeal({
        buyer_organization_id: buyerOrganizationId,
        seller_organization_id: seller,
      });
      onCreated(deal.id);
    } catch (caught) {
      setSubmitError(describeCreateError(caught));
    } finally {
      setSubmitting(false);
    }
  }

  const header = (
    <Reveal className="hero">
      <span className="eyebrow">New deal</span>
      <h1 className="display">
        Open a <span className="gradient-text">draft.</span>
      </h1>
      <p className="hero__lede">
        Start with a buyer and a seller organization. Nothing is binding until both sides approve
        the same version.
      </p>
    </Reveal>
  );

  if (organizationsState.status === "loading") {
    return (
      <div className="workspace">
        {header}
        <section className="card" aria-live="polite">
          <p role="status">Loading organizations…</p>
        </section>
      </div>
    );
  }

  if (organizationsState.status === "error") {
    return (
      <div className="workspace">
        {header}
        <section className="card" role="alert">
          <h2>We could not load your organizations</h2>
          <p className="muted" style={{ marginTop: 10 }}>
            {organizationsState.message}
          </p>
          <div className="actions">
            <button type="button" className="button" onClick={retryOrganizations}>
              Try again
            </button>
          </div>
        </section>
      </div>
    );
  }

  if (organizationsState.status === "empty") {
    return (
      <div className="workspace">
        {header}
        <section className="card">
          <h2>No organizations yet</h2>
          <p className="muted" style={{ marginTop: 10 }}>
            Your account is not an active member of any organization, so you cannot create a deal
            yet.
          </p>
        </section>
      </div>
    );
  }

  return (
    <div className="workspace">
      {header}
      <Reveal delay={80}>
        <section className="card" aria-labelledby="create-deal-heading">
          <div className="panel-head">
            <span className="eyebrow">Draft deal</span>
            <h2 id="create-deal-heading">Create a draft deal</h2>
          </div>
          <p className="muted">
            You act for the buyer organization. The seller must be a different active
            organization.
          </p>
          <form className="form" onSubmit={handleSubmit} noValidate style={{ marginTop: 22 }}>
            <div className="field">
              <label htmlFor="buyer-organization">Buyer organization</label>
              <select
                id="buyer-organization"
                name="buyer-organization"
                value={buyerOrganizationId}
                aria-invalid={fieldErrors.buyer ? true : undefined}
                onChange={(event) => setBuyerOrganizationId(event.target.value)}
              >
                {organizationsState.organizations.map((organization) => (
                  <option key={organization.id} value={organization.id}>
                    {organization.legal_name} ({organization.country_code})
                  </option>
                ))}
              </select>
              {fieldErrors.buyer ? (
                <p className="field-error" role="alert">
                  {fieldErrors.buyer}
                </p>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="seller-organization">Seller organization ID</label>
              <input
                id="seller-organization"
                name="seller-organization"
                type="text"
                placeholder="00000000-0000-0000-0000-000000000000"
                value={sellerOrganizationId}
                aria-invalid={fieldErrors.seller ? true : undefined}
                aria-describedby="seller-organization-hint"
                onChange={(event) => setSellerOrganizationId(event.target.value)}
              />
              <p id="seller-organization-hint" className="hint">
                The seller shares this identifier from their own organization.
              </p>
              {fieldErrors.seller ? (
                <p className="field-error" role="alert">
                  {fieldErrors.seller}
                </p>
              ) : null}
            </div>
            {submitError ? (
              <p className="form-error" role="alert">
                {submitError}
              </p>
            ) : null}
            <button type="submit" className="button" disabled={submitting}>
              {submitting ? "Creating deal…" : "Create deal"}
            </button>
          </form>
        </section>
      </Reveal>
    </div>
  );
}
