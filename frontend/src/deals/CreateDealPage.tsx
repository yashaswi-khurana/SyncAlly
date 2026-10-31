import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, apiRequest, createCounterpartyInvitation, createDeal, listOrganizations } from "../api/client";
import type { Invitation, Organization } from "../api/types";
import Reveal from "../ui/Reveal";

type DirectoryItem = Pick<Organization, "id" | "legal_name" | "country_code">;
type SearchState =
  | { status: "idle" | "loading" }
  | { status: "ready"; items: DirectoryItem[] }
  | { status: "error"; message: string };

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
  const [query, setQuery] = useState("");
  const [seller, setSeller] = useState<DirectoryItem | null>(null);
  const [searchState, setSearchState] = useState<SearchState>({ status: "idle" });
  const [searchRetry, setSearchRetry] = useState(0);
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [reloadCount, setReloadCount] = useState(0);
  const [mode, setMode] = useState<"directory" | "invite">("directory");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [counterpartyName, setCounterpartyName] = useState("");
  const [countryCode, setCountryCode] = useState("US");
  const [invitation, setInvitation] = useState<Invitation | null>(null);
  const [copied, setCopied] = useState(false);

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

  useEffect(() => {
    if (mode !== "directory" || !query.trim() || seller) return;
    let cancelled = false;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void apiRequest<DirectoryItem[]>(
        `/organizations/directory?q=${encodeURIComponent(query.trim())}`,
        { signal: controller.signal },
      ).then(
        (items) => {
          if (!cancelled) setSearchState({ status: "ready", items });
        },
        (caught: unknown) => {
          if (!cancelled) setSearchState({ status: "error", message: describeError(caught) });
        },
      );
    }, 250);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, seller, searchRetry, mode]);

  const results = searchState.status === "ready" ? searchState.items : [];
  const listOpen = searchOpen && results.length > 0;

  function selectSeller(item: DirectoryItem) {
    setSeller(item);
    setQuery(item.legal_name);
    setSearchState({ status: "idle" });
    setSearchOpen(false);
    setActiveIndex(-1);
    setFieldErrors({});
  }

  function retryOrganizations() {
    setOrganizationsState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (submitting) return;
    const nextErrors: FieldErrors = {};
    if (buyerOrganizationId === "") {
      nextErrors.buyer = "Choose the buyer organization.";
    }
    if (mode === "invite") {
      const buyer = organizationsState.status === "ready" ? organizationsState.organizations.find((org) => org.id === buyerOrganizationId) : null;
      if (buyer?.role !== "ADMIN") nextErrors.buyer = "An organization admin is required to invite a counterparty.";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recipientEmail.trim()) || !counterpartyName.trim() || !/^[A-Z]{2}$/.test(countryCode.trim().toUpperCase())) {
        nextErrors.seller = "Enter the counterparty email, company legal name, and two-letter country code.";
      }
    } else if (!seller) {
      nextErrors.seller = "Choose a seller organization from the search results.";
    } else if (seller.id === buyerOrganizationId) {
      nextErrors.seller = "Buyer and seller must be different organizations.";
    }
    setFieldErrors(nextErrors);
    setSubmitError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "invite") {
        const result = await createCounterpartyInvitation({ buyer_organization_id: buyerOrganizationId,
          recipient_email: recipientEmail.trim().toLowerCase(), legal_name: counterpartyName.trim(),
          country_code: countryCode.trim().toUpperCase() });
        setInvitation(result);
        return;
      }
      if (!seller) return;
      const deal = await createDeal({
        buyer_organization_id: buyerOrganizationId,
        seller_organization_id: seller.id,
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
        Start with a buyer and a seller organization. Review shareable conversation facts before
        negotiating terms; fact review does not commit an agreement.
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
          {invitation ? (
            <div className="form" style={{ marginTop: 22 }}>
              <h3>Awaiting counterparty</h3>
              <label htmlFor="counterparty-link">Counterparty invitation link</label>
              <input id="counterparty-link" readOnly value={invitation.invite_url} />
              <p className="muted">Expires {new Date(invitation.expires_at).toLocaleString()}</p>
              <div className="actions">
                <button type="button" className="button" onClick={() => {
                  if (!navigator.clipboard?.writeText) { setSubmitError("Clipboard unavailable. The link is available above."); return; }
                  void navigator.clipboard.writeText(invitation.invite_url).then(() => setCopied(true), () => setSubmitError("Clipboard unavailable. The link is available above."));
                }}>{copied ? "Copied!" : "Copy Link"}</button>
                <button type="button" className="button secondary" onClick={() => invitation.deal_id && onCreated(invitation.deal_id)}>Open pending deal</button>
              </div>
              {submitError ? <p role="alert">{submitError}</p> : null}
            </div>
          ) : <form className="form" onSubmit={handleSubmit} noValidate style={{ marginTop: 22 }}>
            <fieldset disabled={submitting}>
              <legend>Counterparty</legend>
              <label><input type="radio" name="counterparty-mode" checked={mode === "directory"} onChange={() => { setMode("directory"); setFieldErrors({}); }} /> Existing organization</label>
              <label><input type="radio" name="counterparty-mode" checked={mode === "invite"} onChange={() => { setMode("invite"); setFieldErrors({}); }} /> Invite counterparty</label>
            </fieldset>
            <div className="field">
              <label htmlFor="buyer-organization">Buyer organization</label>
              <select
                id="buyer-organization"
                name="buyer-organization"
                value={buyerOrganizationId}
                aria-invalid={fieldErrors.buyer ? true : undefined}
                disabled={submitting}
                onChange={(event) => {
                  setBuyerOrganizationId(event.target.value);
                  setFieldErrors(seller?.id === event.target.value
                    ? { seller: "Buyer and seller must be different organizations." }
                    : {});
                }}
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
            {mode === "invite" ? <>
              <div className="field"><label htmlFor="counterparty-email">Counterparty email</label><input id="counterparty-email" type="email" maxLength={320} disabled={submitting} value={recipientEmail} onChange={(event) => setRecipientEmail(event.target.value)} /></div>
              <div className="field"><label htmlFor="counterparty-name">Counterparty company legal name</label><input id="counterparty-name" maxLength={200} disabled={submitting} value={counterpartyName} onChange={(event) => setCounterpartyName(event.target.value)} /></div>
              <div className="field"><label htmlFor="counterparty-country">Country code</label><input id="counterparty-country" maxLength={2} disabled={submitting} value={countryCode} onChange={(event) => setCountryCode(event.target.value.toUpperCase())} /></div>
              {fieldErrors.seller ? <p role="alert">{fieldErrors.seller}</p> : null}
            </> : <div className="field">
              <label htmlFor="seller-organization">Seller organization</label>
              <input
                id="seller-organization"
                name="seller-organization"
                type="text"
                role="combobox"
                autoComplete="off"
                maxLength={100}
                placeholder="Search by company name"
                value={query}
                disabled={submitting}
                aria-autocomplete="list"
                aria-expanded={listOpen}
                aria-controls={listOpen ? "seller-results" : undefined}
                aria-activedescendant={listOpen && activeIndex >= 0
                  ? `seller-option-${activeIndex}` : undefined}
                aria-invalid={fieldErrors.seller ? true : undefined}
                aria-describedby={fieldErrors.seller ? "seller-error" : "seller-organization-hint"}
                onFocus={() => setSearchOpen(true)}
                onBlur={() => setSearchOpen(false)}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setSeller(null);
                  setSearchState({ status: event.target.value.trim() ? "loading" : "idle" });
                  setSearchOpen(true);
                  setActiveIndex(-1);
                  setFieldErrors({});
                }}
                onKeyDown={(event) => {
                  if (event.key === "Escape") {
                    setSearchOpen(false);
                    setActiveIndex(-1);
                  } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                    event.preventDefault();
                    setSearchOpen(true);
                    if (results.length) setActiveIndex((current) =>
                      event.key === "ArrowDown"
                        ? (current + 1) % results.length
                        : (current <= 0 ? results.length - 1 : current - 1));
                  } else if (event.key === "Enter" && listOpen) {
                    event.preventDefault();
                    if (activeIndex >= 0) selectSeller(results[activeIndex]);
                  }
                }}
              />
              <p id="seller-organization-hint" className="hint">
                Search for a company, then select the seller from the results.
              </p>
              {listOpen ? (
                <ul id="seller-results" role="listbox" aria-label="Seller organizations"
                  style={{ listStyle: "none", padding: 0 }}>
                  {results.map((item, index) => (
                    <li key={item.id} id={`seller-option-${index}`} role="option"
                      aria-selected={activeIndex === index}
                      style={{ padding: 10, cursor: "pointer",
                        background: activeIndex === index ? "var(--accent-soft)" : undefined }}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectSeller(item)}>
                      {item.legal_name} <span className="badge">{item.country_code}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
              {searchState.status === "loading" ? <p role="status">Searching organizations...</p> : null}
              {searchState.status === "ready" && results.length === 0 ? (
                <p role="status">No organizations found. Try another company name.</p>
              ) : null}
              {searchState.status === "error" ? (
                <div role="alert">
                  <p>{searchState.message}</p>
                  <button type="button" className="button" disabled={submitting} onClick={() => {
                    setSearchState({ status: "loading" });
                    setSearchRetry((count) => count + 1);
                    setSearchOpen(true);
                  }}>Retry search</button>
                </div>
              ) : null}
              {fieldErrors.seller ? (
                <p id="seller-error" className="field-error" role="alert">
                  {fieldErrors.seller}
                </p>
              ) : null}
            </div>}
            {submitError ? (
              <p className="form-error" role="alert">
                {submitError}
              </p>
            ) : null}
            <button type="submit" className="button" disabled={submitting}>
              {submitting ? "Creating deal…" : "Create deal"}
            </button>
          </form>}
        </section>
      </Reveal>
    </div>
  );
}
