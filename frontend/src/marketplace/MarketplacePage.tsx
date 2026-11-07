import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createMarketplaceListing, deactivateMarketplaceListing, searchMarketplaceListings, searchOrganizationDirectory } from "../api/client";
import type { CreateMarketplaceListingInput, MarketplaceListing, Organization, OrganizationDirectoryItem, OrganizationDirectorySearch } from "../api/types";
import { navigateToCreateDeal } from "../router";

interface MarketplacePageProps {
  organizations: Organization[];
}

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "The marketplace is unavailable right now.";
}

export default function MarketplacePage({ organizations }: MarketplacePageProps) {
  const [name, setName] = useState("");
  const [product, setProduct] = useState("");
  const [country, setCountry] = useState("");
  const [capability, setCapability] = useState("");
  const [filters, setFilters] = useState<OrganizationDirectorySearch>({});
  const [items, setItems] = useState<OrganizationDirectoryItem[]>([]);
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingListings, setLoadingListings] = useState(true);
  const [error, setError] = useState("");
  const [listingError, setListingError] = useState("");
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

  useEffect(() => {
    const controller = new AbortController();
    void searchOrganizationDirectory(filters, { signal: controller.signal }).then(
      (result) => setItems(result),
      (caught: unknown) => {
        if (!controller.signal.aborted) setError(errorMessage(caught));
      },
    ).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [filters]);

  useEffect(() => {
    const controller = new AbortController();
    void searchMarketplaceListings({
      q: filters.product || filters.q,
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

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setLoadingListings(true);
    setError("");
    setListingError("");
    setFilters({
      q: name.trim() || undefined,
      product: product.trim() || undefined,
      country_code: country.trim().toUpperCase() || undefined,
      capability: capability.trim() || undefined,
    });
  }

  async function publishListing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sellerOrganizationId || savingListing) return;
    setSavingListing(true);
    setListingError("");
    try {
      const listing: CreateMarketplaceListingInput = {
        organization_id: sellerOrganizationId,
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

  const ownOrganizationIds = new Set(organizations.map((organization) => organization.id));
  const adminOrganizations = organizations.filter((organization) => organization.role === "ADMIN");
  const adminOrganizationIds = new Set(adminOrganizations.map((organization) => organization.id));
  const selectedSellerOrganizationId = sellerOrganizationId || adminOrganizations[0]?.id || "";

  return (
    <div className="workspace marketplace-page">
      <header className="hero">
        <span className="eyebrow">Marketplace</span>
        <h1 className="display">Find your next <span className="gradient-text">trade.</span></h1>
        <p className="hero__lede">Discover sellers by product, location, and capability. Product details come from each organization’s public profile.</p>
      </header>

      <form className="card marketplace-page__filters" onSubmit={search}>
        <label>
          Organization
          <input value={name} onChange={(event) => setName(event.target.value)} maxLength={100} placeholder="Company name" />
        </label>
        <label>
          Product or keyword
          <input value={product} onChange={(event) => setProduct(event.target.value)} maxLength={100} placeholder="Grain, textiles, machinery…" />
        </label>
        <label>
          Country code
          <input value={country} onChange={(event) => setCountry(event.target.value.toUpperCase())} maxLength={2} placeholder="IN" />
        </label>
        <label>
          Capability
          <input value={capability} onChange={(event) => setCapability(event.target.value)} maxLength={100} placeholder="Wholesale, manufacturing…" />
        </label>
        <button className="button" type="submit" disabled={loading}>Search marketplace</button>
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

      <section className="marketplace-page__listings" aria-label="Product listings" aria-live="polite">
        <div className="section-heading"><div><span className="eyebrow">Available now</span><h2>Product listings</h2></div></div>
        {loadingListings ? <p role="status">Loading product listings…</p> : null}
        {!loadingListings && listings.length === 0 && !listingError ? <p className="muted">No matching product listings yet.</p> : null}
        {listings.map((listing) => (
          <article className="card marketplace-page__listing" key={listing.id}>
            <div className="marketplace-page__item-heading">
              <div><span className="eyebrow">{listing.category} · {listing.country_code}</span><h3>{listing.title}</h3></div>
              <strong>{listing.unit_price} {listing.currency} / {listing.unit}</strong>
            </div>
            <p>{listing.organization_name} · {listing.available_quantity} {listing.unit} available</p>
            {listing.description ? <p className="muted">{listing.description}</p> : null}
            {adminOrganizationIds.has(listing.organization_id) ? (
              <button className="button ghost" type="button" disabled={deactivatingId === listing.id} onClick={() => void takeDownListing(listing.id)}>
                {deactivatingId === listing.id ? "Taking down…" : "Take down listing"}
              </button>
            ) : !ownOrganizationIds.has(listing.organization_id) && organizations.length > 0 ? (
              <button className="button secondary" type="button" onClick={() => navigateToCreateDeal(listing.organization_id)}>Start a deal</button>
            ) : null}
          </article>
        ))}
        {listingError ? <p role="alert">{listingError}</p> : null}
      </section>

      <section className="marketplace-page__results" aria-label="Marketplace results" aria-live="polite">
        {loading ? <p role="status">Searching organizations…</p> : null}
        {error ? <p role="alert">{error}</p> : null}
        {!loading && !error && items.length === 0 ? <p className="muted">No organizations match these filters.</p> : null}
        {items.map((item) => (
          <article className="card marketplace-page__item" key={item.id}>
            <div className="marketplace-page__item-heading">
              <div>
                <span className="eyebrow">{item.country_code}</span>
                <h2>{item.legal_name}</h2>
              </div>
              {ownOrganizationIds.has(item.id) ? <span className="hint">Your organization</span> : null}
            </div>
            {item.products?.length ? (
              <div>
                <h3>Products</h3>
                <p>{item.products.join(" · ")}</p>
              </div>
            ) : <p className="muted">No products listed yet.</p>}
            {item.capabilities?.length ? <p><strong>Capabilities:</strong> {item.capabilities.join(" · ")}</p> : null}
            {item.regions?.length ? <p><strong>Markets served:</strong> {item.regions.join(" · ")}</p> : null}
            {!ownOrganizationIds.has(item.id) && organizations.length > 0 ? (
              <button className="button secondary" type="button" onClick={() => navigateToCreateDeal(item.id)}>
                Start a deal
              </button>
            ) : null}
          </article>
        ))}
        {!loading && !error && items.length === 100 ? <p className="hint">Showing the first 100 results. Add filters to narrow your search.</p> : null}
      </section>
    </div>
  );
}
