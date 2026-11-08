import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, closeMarketplaceRFQ, createMarketplaceListing, createMarketplaceRFQ, deactivateMarketplaceListing, searchMarketplaceListings, searchMarketplaceRFQs } from "../api/client";
import type { CreateMarketplaceListingInput, CreateMarketplaceRFQInput, MarketplaceListing, MarketplaceRFQ, Organization } from "../api/types";
import { navigateToCreateDeal } from "../router";

interface MarketplacePageProps {
  organizations: Organization[];
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "The marketplace is unavailable right now.";
}

function compactDecimal(value: string): string {
  const [integer, fraction] = value.split(".");
  if (fraction === undefined) return value;
  const trimmedFraction = fraction.replace(/0+$/, "");
  return trimmedFraction ? `${integer}.${trimmedFraction}` : integer;
}

export default function MarketplacePage({ organizations }: MarketplacePageProps) {
  const [product, setProduct] = useState("");
  const [country, setCountry] = useState("");
  const [filters, setFilters] = useState<{ product?: string; country_code?: string }>({});
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [rfqs, setRfqs] = useState<MarketplaceRFQ[]>([]);
  const [loadingListings, setLoadingListings] = useState(true);
  const [loadingRfqs, setLoadingRfqs] = useState(true);
  const [listingError, setListingError] = useState("");
  const [rfqError, setRfqError] = useState("");
  const [sellerOrganizationId, setSellerOrganizationId] = useState("");
  const [listingTitle, setListingTitle] = useState("");
  const [listingDescription, setListingDescription] = useState("");
  const [listingCategory, setListingCategory] = useState("");
  const [listingQuantity, setListingQuantity] = useState("");
  const [listingUnit, setListingUnit] = useState("");
  const [listingPrice, setListingPrice] = useState("");
  const [listingCurrency, setListingCurrency] = useState("USD");
  const [savingListing, setSavingListing] = useState(false);
  const [listingRefresh, setListingRefresh] = useState(0);
  const [deactivatingId, setDeactivatingId] = useState("");
  const [buyerOrganizationId, setBuyerOrganizationId] = useState("");
  const [rfqTitle, setRfqTitle] = useState("");
  const [rfqDescription, setRfqDescription] = useState("");
  const [rfqCategory, setRfqCategory] = useState("");
  const [rfqQuantity, setRfqQuantity] = useState("");
  const [rfqUnit, setRfqUnit] = useState("");
  const [rfqDestination, setRfqDestination] = useState("");
  const [rfqDeliveryDate, setRfqDeliveryDate] = useState("");
  const [rfqTargetPrice, setRfqTargetPrice] = useState("");
  const [rfqCurrency, setRfqCurrency] = useState("USD");
  const [savingRfq, setSavingRfq] = useState(false);
  const [rfqRefresh, setRfqRefresh] = useState(0);
  const [closingRfqId, setClosingRfqId] = useState("");
  const ownOrganizationIds = new Set(organizations.map((organization) => organization.id));
  const adminOrganizations = organizations.filter((organization) => organization.role === "ADMIN");
  const adminOrganizationIds = new Set(adminOrganizations.map((organization) => organization.id));
  const selectedSellerOrganizationId = sellerOrganizationId || adminOrganizations[0]?.id || "";
  const selectedBuyerOrganizationId = buyerOrganizationId || adminOrganizations[0]?.id || "";

  useEffect(() => {
    const controller = new AbortController();
    void searchMarketplaceListings({
      q: filters.product,
      country_code: filters.country_code,
    }, { signal: controller.signal }).then(
      (result) => {
        setListings(result);
        setListingError("");
      },
      (caught: unknown) => {
        if (!controller.signal.aborted) setListingError(errorMessage(caught));
      },
    ).finally(() => {
      if (!controller.signal.aborted) setLoadingListings(false);
    });
    return () => controller.abort();
  }, [filters, listingRefresh]);

  useEffect(() => {
    const controller = new AbortController();
    void searchMarketplaceRFQs({
      q: filters.product,
      destination_country_code: filters.country_code,
    }, { signal: controller.signal }).then(
      (result) => {
        setRfqs(result);
        setRfqError("");
      },
      (caught: unknown) => {
        if (!controller.signal.aborted) setRfqError(errorMessage(caught));
      },
    ).finally(() => {
      if (!controller.signal.aborted) setLoadingRfqs(false);
    });
    return () => controller.abort();
  }, [filters, rfqRefresh]);

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoadingListings(true);
    setLoadingRfqs(true);
    setListingError("");
    setRfqError("");
    setFilters({
      product: product.trim() || undefined,
      country_code: country.trim().toUpperCase() || undefined,
    });
  }

  async function publishRfq(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedBuyerOrganizationId || savingRfq) return;
    setSavingRfq(true);
    setRfqError("");
    try {
      const request: CreateMarketplaceRFQInput = {
        organization_id: selectedBuyerOrganizationId,
        title: rfqTitle.trim(),
        description: rfqDescription.trim(),
        category: rfqCategory.trim(),
        quantity: rfqQuantity,
        unit: rfqUnit.trim(),
        destination_country_code: rfqDestination.trim().toUpperCase(),
        target_delivery_date: rfqDeliveryDate || null,
        target_unit_price: rfqTargetPrice || null,
        currency: rfqTargetPrice ? rfqCurrency.trim().toUpperCase() : null,
      };
      await createMarketplaceRFQ(request);
      setRfqTitle("");
      setRfqDescription("");
      setRfqCategory("");
      setRfqQuantity("");
      setRfqUnit("");
      setRfqDeliveryDate("");
      setRfqTargetPrice("");
      setLoadingRfqs(true);
      setRfqRefresh((count) => count + 1);
    } catch (caught: unknown) {
      setRfqError(errorMessage(caught));
    } finally {
      setSavingRfq(false);
    }
  }

  async function closeRfq(rfqId: string) {
    setClosingRfqId(rfqId);
    setRfqError("");
    try {
      await closeMarketplaceRFQ(rfqId);
      setLoadingRfqs(true);
      setRfqRefresh((count) => count + 1);
    } catch (caught: unknown) {
      setRfqError(errorMessage(caught));
    } finally {
      setClosingRfqId("");
    }
  }

  async function publishListing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedSellerOrganizationId || savingListing) return;
    setSavingListing(true);
    setListingError("");
    try {
      const listing: CreateMarketplaceListingInput = {
        organization_id: selectedSellerOrganizationId,
        title: listingTitle.trim(),
        description: listingDescription.trim(),
        category: listingCategory.trim(),
        available_quantity: listingQuantity,
        unit: listingUnit.trim(),
        unit_price: listingPrice,
        currency: listingCurrency.trim().toUpperCase(),
      };
      await createMarketplaceListing(listing);
      setListingTitle("");
      setListingDescription("");
      setListingCategory("");
      setListingQuantity("");
      setListingUnit("");
      setListingPrice("");
      setLoadingListings(true);
      setListingRefresh((count) => count + 1);
    } catch (caught: unknown) {
      setListingError(errorMessage(caught));
    } finally {
      setSavingListing(false);
    }
  }

  async function takeDownListing(listingId: string) {
    setDeactivatingId(listingId);
    setListingError("");
    try {
      await deactivateMarketplaceListing(listingId);
      setLoadingListings(true);
      setListingRefresh((count) => count + 1);
    } catch (caught: unknown) {
      setListingError(errorMessage(caught));
    } finally {
      setDeactivatingId("");
    }
  }

  return (
    <div className="workspace marketplace-page">
      <header className="hero">
        <span className="eyebrow">Marketplace</span>
        <h1 className="display">Find your next <span className="gradient-text">trade.</span></h1>
        <p className="hero__lede">Browse active product listings and buyer requests.</p>
      </header>

      <form className="card marketplace-page__filters" onSubmit={search}>
        <label>
          Product or keyword
          <input value={product} onChange={(event) => setProduct(event.target.value)} maxLength={100} placeholder="Grain, textiles, machinery…" />
        </label>
        <label>
          Country code
          <input value={country} onChange={(event) => setCountry(event.target.value.toUpperCase())} maxLength={2} placeholder="IN" />
        </label>
        <button className="button" type="submit" disabled={loadingListings || loadingRfqs}>Search marketplace</button>
      </form>

      {adminOrganizations.length > 0 ? (
        <form className="card marketplace-page__publish" onSubmit={(event) => void publishListing(event)}>
          <div>
            <span className="eyebrow">Seller tools</span>
            <h2>Publish a product listing</h2>
          </div>
          {adminOrganizations.length > 1 ? (
            <label>
              Seller organization
              <select value={selectedSellerOrganizationId} onChange={(event) => setSellerOrganizationId(event.target.value)} disabled={savingListing}>
                {adminOrganizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.legal_name}</option>)}
              </select>
            </label>
          ) : null}
          <label>Product name<input value={listingTitle} onChange={(event) => setListingTitle(event.target.value)} maxLength={200} required disabled={savingListing} /></label>
          <label>Category<input value={listingCategory} onChange={(event) => setListingCategory(event.target.value)} maxLength={100} required disabled={savingListing} /></label>
          <label>Description<textarea value={listingDescription} onChange={(event) => setListingDescription(event.target.value)} maxLength={2000} rows={2} disabled={savingListing} /></label>
          <div className="marketplace-page__price-fields">
            <label>Available quantity<input type="number" min="0.000001" step="any" value={listingQuantity} onChange={(event) => setListingQuantity(event.target.value)} required disabled={savingListing} /></label>
            <label>Unit<input value={listingUnit} onChange={(event) => setListingUnit(event.target.value)} maxLength={32} placeholder="kg, boxes…" required disabled={savingListing} /></label>
            <label>Unit price<input type="number" min="0" step="any" value={listingPrice} onChange={(event) => setListingPrice(event.target.value)} required disabled={savingListing} /></label>
            <label>Currency<input value={listingCurrency} onChange={(event) => setListingCurrency(event.target.value.toUpperCase())} minLength={3} maxLength={3} required disabled={savingListing} /></label>
          </div>
          <button className="button" type="submit" disabled={savingListing || !listingTitle.trim() || !listingCategory.trim() || !listingQuantity || !listingUnit.trim() || !listingPrice}>
            {savingListing ? "Publishing…" : "Publish listing"}
          </button>
          {listingError ? <p role="alert">{listingError}</p> : null}
        </form>
      ) : null}

      {adminOrganizations.length > 0 ? (
        <form className="card marketplace-page__publish" onSubmit={(event) => void publishRfq(event)}>
          <div>
            <span className="eyebrow">Buyer tools</span>
            <h2>Request a supplier quote</h2>
          </div>
          {adminOrganizations.length > 1 ? (
            <label>
              Buyer organization
              <select value={selectedBuyerOrganizationId} onChange={(event) => setBuyerOrganizationId(event.target.value)} disabled={savingRfq}>
                {adminOrganizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.legal_name}</option>)}
              </select>
            </label>
          ) : null}
          <label>Product or specification<input value={rfqTitle} onChange={(event) => setRfqTitle(event.target.value)} maxLength={200} required disabled={savingRfq} /></label>
          <label>Category<input value={rfqCategory} onChange={(event) => setRfqCategory(event.target.value)} maxLength={100} required disabled={savingRfq} /></label>
          <label>Requirements<textarea value={rfqDescription} onChange={(event) => setRfqDescription(event.target.value)} maxLength={2000} rows={2} disabled={savingRfq} /></label>
          <div className="marketplace-page__price-fields">
            <label>Quantity<input type="number" min="0.000001" step="any" value={rfqQuantity} onChange={(event) => setRfqQuantity(event.target.value)} required disabled={savingRfq} /></label>
            <label>Unit<input value={rfqUnit} onChange={(event) => setRfqUnit(event.target.value)} maxLength={32} placeholder="kg, boxes…" required disabled={savingRfq} /></label>
            <label>Deliver to country code<input value={rfqDestination} onChange={(event) => setRfqDestination(event.target.value.toUpperCase())} minLength={2} maxLength={2} placeholder="IN" required disabled={savingRfq} /></label>
            <label>Needed by<input type="date" value={rfqDeliveryDate} onChange={(event) => setRfqDeliveryDate(event.target.value)} disabled={savingRfq} /></label>
          </div>
          <div className="marketplace-page__price-fields">
            <label>Target unit price (optional)<input type="number" min="0" step="any" value={rfqTargetPrice} onChange={(event) => setRfqTargetPrice(event.target.value)} disabled={savingRfq} /></label>
            {rfqTargetPrice ? <label>Currency<input value={rfqCurrency} onChange={(event) => setRfqCurrency(event.target.value.toUpperCase())} minLength={3} maxLength={3} required disabled={savingRfq} /></label> : null}
          </div>
          <button className="button" type="submit" disabled={savingRfq || !rfqTitle.trim() || !rfqCategory.trim() || !rfqQuantity || !rfqUnit.trim() || !/^[A-Z]{2}$/.test(rfqDestination.trim().toUpperCase())}>
            {savingRfq ? "Publishing…" : "Publish request"}
          </button>
          {rfqError ? <p role="alert">{rfqError}</p> : null}
        </form>
      ) : null}

      <section className="marketplace-page__requests" aria-label="Buyer requests for quote" aria-live="polite">
        <div className="section-heading"><div><span className="eyebrow">Buyer demand</span><h2>Requests for quote</h2></div></div>
        {loadingRfqs ? <p role="status">Loading buyer requests…</p> : null}
        {!loadingRfqs && rfqs.length === 0 && !rfqError ? <p className="muted">No matching buyer requests yet.</p> : null}
        {rfqs.map((rfq) => (
          <article className="card marketplace-page__listing" key={rfq.id}>
            <div className="marketplace-page__item-heading">
              <div><span className="eyebrow">{rfq.category} · Deliver to {rfq.destination_country_code}</span><h3>{rfq.title}</h3></div>
              <strong>{compactDecimal(rfq.quantity)} {rfq.unit}</strong>
            </div>
            <p>{rfq.organization_name} · {rfq.organization_country_code}{rfq.target_delivery_date ? ` · Needed by ${rfq.target_delivery_date}` : ""}</p>
            {rfq.target_unit_price && rfq.currency ? <p>Target price: {compactDecimal(rfq.target_unit_price)} {rfq.currency} / {rfq.unit}</p> : null}
            {rfq.description ? <p className="muted">{rfq.description}</p> : null}
            {adminOrganizationIds.has(rfq.organization_id) ? (
              <button className="button ghost" type="button" disabled={closingRfqId === rfq.id} onClick={() => void closeRfq(rfq.id)}>
                {closingRfqId === rfq.id ? "Closing…" : "Close request"}
              </button>
            ) : !ownOrganizationIds.has(rfq.organization_id) && organizations.length > 0 ? (
              <button className="button secondary" type="button" onClick={() => navigateToCreateDeal(rfq.organization_id, "SELLER", rfq.id)}>Respond to request</button>
            ) : null}
          </article>
        ))}
        {rfqError ? <p role="alert">{rfqError}</p> : null}
      </section>

      <section className="marketplace-page__listings" aria-label="Product listings" aria-live="polite">
        <div className="section-heading"><div><span className="eyebrow">Available now</span><h2>Product listings</h2></div></div>
        {loadingListings ? <p role="status">Loading product listings…</p> : null}
        {!loadingListings && listings.length === 0 && !listingError ? <p className="muted">No matching product listings yet.</p> : null}
        {listings.map((listing) => (
          <article className="card marketplace-page__listing" key={listing.id}>
            <div className="marketplace-page__item-heading">
              <div><span className="eyebrow">{listing.category} · {listing.country_code}</span><h3>{listing.title}</h3></div>
              <strong>{compactDecimal(listing.unit_price)} {listing.currency} / {listing.unit}</strong>
            </div>
            <p>{listing.organization_name} · {compactDecimal(listing.available_quantity)} {listing.unit} available</p>
            {listing.description ? <p className="muted">{listing.description}</p> : null}
            {adminOrganizationIds.has(listing.organization_id) ? (
              <button className="button ghost" type="button" disabled={deactivatingId === listing.id} onClick={() => void takeDownListing(listing.id)}>
                {deactivatingId === listing.id ? "Taking down…" : "Take down listing"}
              </button>
            ) : !ownOrganizationIds.has(listing.organization_id) && organizations.length > 0 ? (
              <button className="button secondary" type="button" onClick={() => navigateToCreateDeal(listing.organization_id, "BUYER", undefined, listing.id)}>Start a deal</button>
            ) : null}
          </article>
        ))}
        {listingError ? <p role="alert">{listingError}</p> : null}
      </section>

    </div>
  );
}
