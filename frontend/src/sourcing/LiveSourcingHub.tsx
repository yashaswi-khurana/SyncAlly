import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { getMarketplaceListing, interpretSourcingRequirements, searchMarketplaceListings } from "../api/client";
import type { InterpretSourcingResponse, MarketplaceListing } from "../api/types";
import { compactDecimal } from "../formatting";
import { navigateToCreateDeal } from "../router";
import SplitText from "../ui/SplitText";
import type { SourcingHubProps } from "./sourcingTypes";

const PAGE_SIZE = 25;

export default function LiveSourcingHub({ organizations = [], initialListingId, onDealInitiated }: SourcingHubProps) {
  const [prompt, setPrompt] = useState("");
  const [interpretation, setInterpretation] = useState<InterpretSourcingResponse | null>(null);
  const [interpreting, setInterpreting] = useState(false);
  const [interpretError, setInterpretError] = useState("");
  const interpretationRequest = useRef<AbortController | null>(null);
  const [keyword, setKeyword] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [searchVersion, setSearchVersion] = useState(0);
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [listingError, setListingError] = useState("");
  const [selected, setSelected] = useState<MarketplaceListing[]>([]);
  const [linkedListing, setLinkedListing] = useState<MarketplaceListing | null>(null);
  const [linkedError, setLinkedError] = useState<{ id: string; message: string } | null>(null);
  const ownOrganizations = new Set(organizations.map((organization) => organization.id));

  useEffect(() => () => interpretationRequest.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    void searchMarketplaceListings({ q: query || undefined }, {
      signal: controller.signal, limit: PAGE_SIZE, offset,
    }).then(
      (result) => { if (!controller.signal.aborted) setListings(result); },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setListingError(error instanceof Error ? error.message : "Could not load marketplace offers.");
        }
      },
    ).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, offset, searchVersion]);

  useEffect(() => {
    if (!initialListingId) return;
    const controller = new AbortController();
    void getMarketplaceListing(initialListingId, { signal: controller.signal }).then(
      (listing) => {
        if (!controller.signal.aborted) {
          setLinkedError(null);
          setLinkedListing(listing);
        }
      },
      (error: unknown) => {
        if (!controller.signal.aborted) {
          setLinkedListing(null);
          setLinkedError({ id: initialListingId, message: error instanceof Error ? error.message : "Could not load the linked offer." });
        }
      },
    );
    return () => controller.abort();
  }, [initialListingId]);

  async function interpret(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!prompt.trim() || interpreting) return;
    interpretationRequest.current?.abort();
    const controller = new AbortController();
    interpretationRequest.current = controller;
    setInterpreting(true);
    setInterpretError("");
    setInterpretation(null);
    try {
      const result = await interpretSourcingRequirements({ prompt: prompt.trim() }, { signal: controller.signal });
      if (controller.signal.aborted) return;
      setInterpretation(result);
      setKeyword(result.requirements.title.slice(0, 100));
    } catch (error) {
      if (!controller.signal.aborted) {
        setInterpretError(error instanceof Error ? error.message : "Could not interpret requirements.");
      }
    } finally {
      if (!controller.signal.aborted) setInterpreting(false);
    }
  }

  function changePrompt(value: string) {
    interpretationRequest.current?.abort();
    setInterpreting(false);
    setPrompt(value);
    setInterpretation(null);
    setInterpretError("");
  }

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSelected([]);
    setLoading(true);
    setListingError("");
    setListings([]);
    setOffset(0);
    setQuery(keyword.trim());
    setSearchVersion((value) => value + 1);
  }

  function changePage(nextOffset: number) {
    setLoading(true);
    setListingError("");
    setListings([]);
    setOffset(nextOffset);
  }

  function toggleListing(listing: MarketplaceListing) {
    setSelected((current) => current.some((item) => item.id === listing.id)
      ? current.filter((item) => item.id !== listing.id)
      : [...current, listing]);
  }

  function listingCard(listing: MarketplaceListing) {
    const checked = selected.some((item) => item.id === listing.id);
    return (
      <article className="card marketplace-page__listing" key={listing.id}>
        <div className="marketplace-page__item-heading">
          <div><span className="eyebrow">{listing.category} · {listing.country_code}</span><h3>{listing.title}</h3></div>
          <strong>{compactDecimal(listing.unit_price)} {listing.currency} / {listing.unit}</strong>
        </div>
        <p>{listing.organization_name} · {compactDecimal(listing.available_quantity)} {listing.unit} available</p>
        {listing.description && <p>{listing.description}</p>}
        <p className="muted">Lead time, certifications, warranty and shipping terms are not structured listing fields; confirm them with the seller.</p>
        <div className="panel-actions">
          <label>
            <input type="checkbox" checked={checked} disabled={!checked && selected.length >= 3} onChange={() => toggleListing(listing)} />
            Compare {listing.title} from {listing.organization_name}
          </label>
          {!ownOrganizations.has(listing.organization_id) && organizations.length > 0 && (
            <button type="button" className="button secondary" onClick={() => {
              navigateToCreateDeal(listing.organization_id, "BUYER", undefined, listing.id);
              onDealInitiated?.(window.location.hash);
            }}>Start a deal</button>
          )}
        </div>
      </article>
    );
  }

  const requirements = interpretation?.requirements;
  return (
    <div className="sourcing-hub-container" data-testid="sourcing-hub-page">
      <header className="sourcing-hub-header">
        <nav aria-label="Breadcrumb" className="breadcrumbs"><span>Marketplace</span> &gt; <span>Sourcing Hub</span></nav>
        <h1><SplitText text="Buyer Sourcing Agent" /></h1>
        <p className="subtitle">Describe what you need, then review and compare active marketplace offers.</p>
      </header>

      <form className="card sourcing-requirement-card" onSubmit={(event) => void interpret(event)}>
        <div><span className="eyebrow">AI-assisted requirements</span><h2>Describe your requirements</h2></div>
        <label htmlFor="sourcing-prompt">What are you looking for?</label>
        <textarea id="sourcing-prompt" rows={4} maxLength={8000} value={prompt}
          onChange={(event) => changePrompt(event.target.value)}
          placeholder="Describe the product and category, quantity and unit, destination country, currency, warranty and inspection requirements." />
        <p className="muted">Your submitted text is sent to the configured AI provider. Review its interpretation before using it.</p>
        {interpretError && <p role="alert">{interpretError}</p>}
        <div><button className="button" type="submit" disabled={!prompt.trim() || interpreting}>
          {interpreting ? "Interpreting…" : "Interpret requirements"}
        </button></div>
      </form>

      {requirements && (
        <section className="card sourcing-requirement-card" aria-label="Review interpreted requirements">
          <h2>Review interpreted requirements</h2>
          <p>Source: {interpretation.ai_provider || "configured provider"}{interpretation.ai_model ? ` · ${interpretation.ai_model}` : ""}</p>
          <p>{requirements.title} · {requirements.category}</p>
          {requirements.description && <p>{requirements.description}</p>}
          <p>{requirements.quantity.target_quantity} {requirements.quantity.unit} to {requirements.delivery.destination_country_code}</p>
          {requirements.delivery.destination_port_or_city && <p>Destination: {requirements.delivery.destination_port_or_city}</p>}
          {requirements.delivery.required_delivery_date && <p>Required by: {requirements.delivery.required_delivery_date}</p>}
          {requirements.delivery.max_lead_time_days != null && <p>Maximum lead time: {requirements.delivery.max_lead_time_days} days</p>}
          <p>Currency: {requirements.pricing.currency}; target price: {requirements.pricing.target_unit_price ?? "not specified"};
            maximum price: {requirements.pricing.max_unit_price ?? "not specified"}; total budget: {requirements.pricing.max_total_budget ?? "not specified"}</p>
          <p>Warranty: {requirements.commercial_terms.min_warranty_months} months; inspection: {requirements.commercial_terms.inspection_requirement}</p>
          <p>Materials: {requirements.technical_specs.materials.join(", ") || "not specified"}; certifications: {requirements.technical_specs.certifications.join(", ") || "not specified"}; standards: {requirements.technical_specs.standards.join(", ") || "not specified"}</p>
          {requirements.technical_specs.quality_grade && <p>Quality grade: {requirements.technical_specs.quality_grade}</p>}
          {requirements.technical_specs.tolerances && <p>Tolerances: {requirements.technical_specs.tolerances}</p>}
          {requirements.technical_specs.notes && <p>Technical notes: {requirements.technical_specs.notes}</p>}
          {requirements.quantity.min_acceptable_quantity != null && <p>Minimum quantity: {requirements.quantity.min_acceptable_quantity} {requirements.quantity.unit}</p>}
          {requirements.quantity.packaging_preference && <p>Packaging: {requirements.quantity.packaging_preference}</p>}
          <p>Preferred Incoterm: {requirements.commercial_terms.preferred_incoterm || "not specified"}; acceptable Incoterms: {requirements.commercial_terms.acceptable_incoterms.join(", ") || "not specified"}; payment: {requirements.commercial_terms.preferred_payment_term || "not specified"}</p>
          <p>Review and edit the search keyword below; it does not automatically filter on every requirement.</p>
        </section>
      )}

      <form className="card marketplace-page__filters" onSubmit={search}>
        <label>Product or keyword
          <input value={keyword} onChange={(event) => setKeyword(event.target.value)} maxLength={100} placeholder="Search active offers" />
        </label>
        <button className="button" type="submit" disabled={loading}>Search offers</button>
      </form>

      {linkedError && linkedError.id === initialListingId && <p role="alert">{linkedError.message}</p>}
      {linkedListing && linkedListing.id === initialListingId && !listings.some((item) => item.id === linkedListing.id) && (
        <section aria-label="Linked offer"><h2>Linked offer</h2>{listingCard(linkedListing)}</section>
      )}
      <section className="marketplace-page__listings" aria-label="Marketplace offers" aria-live="polite">
        <h2>Active marketplace offers</h2>
        <p className="muted">Listings are seller-provided and not verified. Select up to three to compare their stated details.</p>
        {loading && <p role="status">Loading offers…</p>}
        {listingError && <p role="alert">{listingError}</p>}
        {!loading && !listingError && listings.length === 0 && <p>No offers found. Try a different keyword or browse all offers.</p>}
        {listings.map(listingCard)}
        <div className="panel-actions">
          <button type="button" className="button ghost" disabled={loading || offset === 0} onClick={() => changePage(Math.max(0, offset - PAGE_SIZE))}>Previous</button>
          <button type="button" className="button ghost" disabled={loading || listings.length < PAGE_SIZE || offset >= 10000} onClick={() => changePage(offset + PAGE_SIZE)}>Next</button>
        </div>
      </section>

      {selected.length > 0 && (
        <section className="card sourcing-requirement-card" aria-label="Offer comparison">
          <h2>Compare stated offer details</h2>
          <p className="muted">No match score is assigned. Confirm missing details with each seller before committing.</p>
          <div className="sourcing-offer-table-wrap">
            <table className="sourcing-offer-table">
              <thead><tr><th scope="col">Detail</th><th scope="col">Your requirement</th>
                {selected.map((listing) => (
                  <th scope="col" key={listing.id}>
                    {listing.organization_name} · {listing.title}
                    <button type="button" className="button ghost" onClick={() => toggleListing(listing)}
                      aria-label={`Remove ${listing.title} from ${listing.organization_name} from comparison`}>Remove</button>
                  </th>
                ))}
              </tr></thead>
              <tbody>
                <tr><th scope="row">Product</th><td>{requirements?.title || "Not provided"}</td>
                  {selected.map((listing) => <td key={listing.id}>{listing.title}</td>)}</tr>
                <tr><th scope="row">Quantity</th><td>{requirements ? `${requirements.quantity.target_quantity} ${requirements.quantity.unit}` : "Not provided"}</td>
                  {selected.map((listing) => <td key={listing.id}>{compactDecimal(listing.available_quantity)} {listing.unit} available</td>)}</tr>
                <tr><th scope="row">Unit price</th><td>{requirements?.pricing.target_unit_price ? `${requirements.pricing.target_unit_price} ${requirements.pricing.currency} / ${requirements.quantity.unit}` : "Not provided"}</td>
                  {selected.map((listing) => <td key={listing.id}>{compactDecimal(listing.unit_price)} {listing.currency} / {listing.unit}</td>)}</tr>
                <tr><th scope="row">Seller country</th><td>—</td>
                  {selected.map((listing) => <td key={listing.id}>{listing.country_code}</td>)}</tr>
                <tr><th scope="row">Other terms</th><td>{requirements ? "See reviewed requirements above" : "Not provided"}</td>
                  {selected.map((listing) => <td key={listing.id}>Not structured listing fields; confirm with seller</td>)}</tr>
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
