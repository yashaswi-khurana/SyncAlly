import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, deactivateMarketplaceListing, searchMarketplaceListings } from "../api/client";
import type { MarketplaceListing, Organization } from "../api/types";
import { compactDecimal } from "../formatting";
import { navigateToCreateDeal } from "../router";
import SplitText from "../ui/SplitText";

interface ProductListingsPageProps {
  organizations: Organization[];
}

const LISTING_PAGE_SIZE = 20;
const LISTING_FETCH_LIMIT = 100;

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "The marketplace is unavailable right now.";
}

export default function ProductListingsPage({ organizations }: ProductListingsPageProps) {
  const [product, setProduct] = useState("");
  const [type, setType] = useState("");
  const [dealer, setDealer] = useState("");
  const [country, setCountry] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [filters, setFilters] = useState<{ product?: string; country_code?: string; category?: string; dealer?: string; min_price?: string; max_price?: string }>({});
  const [listings, setListings] = useState<MarketplaceListing[]>([]);
  const [visibleListingCount, setVisibleListingCount] = useState(LISTING_PAGE_SIZE);
  const [hasMoreOnServer, setHasMoreOnServer] = useState(false);
  const [loadingListings, setLoadingListings] = useState(true);
  const [loadingMoreListings, setLoadingMoreListings] = useState(false);
  const [listingError, setListingError] = useState("");
  const [listingRefresh, setListingRefresh] = useState(0);
  const [deactivatingId, setDeactivatingId] = useState("");
  const ownOrganizationIds = new Set(organizations.map((organization) => organization.id));
  const adminOrganizationIds = new Set(organizations.filter((organization) => organization.role === "ADMIN").map((organization) => organization.id));

  useEffect(() => {
    const controller = new AbortController();
    void searchMarketplaceListings({
      q: filters.product,
      country_code: filters.country_code,
      category: filters.category,
      dealer: filters.dealer,
      min_price: filters.min_price,
      max_price: filters.max_price,
    }, { signal: controller.signal, limit: LISTING_FETCH_LIMIT, offset: 0 }).then(
      (result) => {
        setListings(result);
        setVisibleListingCount(LISTING_PAGE_SIZE);
        setHasMoreOnServer(result.length === LISTING_FETCH_LIMIT);
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

  async function loadMoreListings() {
    if (visibleListingCount < listings.length) {
      setVisibleListingCount((count) => Math.min(count + LISTING_PAGE_SIZE, listings.length));
      return;
    }
    if (!hasMoreOnServer || loadingMoreListings) return;
    setLoadingMoreListings(true);
    try {
      const nextPage = await searchMarketplaceListings({
        q: filters.product,
        country_code: filters.country_code,
        category: filters.category,
        dealer: filters.dealer,
        min_price: filters.min_price,
        max_price: filters.max_price,
      }, { limit: LISTING_FETCH_LIMIT, offset: listings.length });
      setListings((previous) => [...previous, ...nextPage]);
      setVisibleListingCount((count) => count + LISTING_PAGE_SIZE);
      setHasMoreOnServer(nextPage.length === LISTING_FETCH_LIMIT);
    } catch (caught: unknown) {
      setListingError(errorMessage(caught));
    } finally {
      setLoadingMoreListings(false);
    }
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoadingListings(true);
    setListingError("");
    setFilters({
      product: product.trim() || undefined,
      country_code: country.trim().toUpperCase() || undefined,
      category: type.trim() || undefined,
      dealer: dealer.trim() || undefined,
      min_price: minPrice || undefined,
      max_price: maxPrice || undefined,
    });
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
    <div className="workspace listings-page">
      <header className="hero">
        <span className="eyebrow">Marketplace</span>
        <h1 className="display"><SplitText text="Browse product listings." accent="listings." /></h1>
        <p className="hero__lede">Search and filter active offers from every seller on the network.</p>
      </header>

      <form className="card listings-page__filters" onSubmit={applyFilters}>
        <label>
          Product or keyword
          <input value={product} onChange={(event) => setProduct(event.target.value)} maxLength={100} placeholder="Grain, textiles, machinery…" />
        </label>
        <label>
          Type / category
          <input value={type} onChange={(event) => setType(event.target.value)} maxLength={100} placeholder="Fasteners, grain…" />
        </label>
        <label>
          Dealer
          <input value={dealer} onChange={(event) => setDealer(event.target.value)} maxLength={200} placeholder="Seller name" />
        </label>
        <label>
          Country code
          <input value={country} onChange={(event) => setCountry(event.target.value.toUpperCase())} maxLength={2} placeholder="IN" />
        </label>
        <label>
          Min price
          <input type="number" min="0" step="any" value={minPrice} onChange={(event) => setMinPrice(event.target.value)} placeholder="0" />
        </label>
        <label>
          Max price
          <input type="number" min="0" step="any" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} placeholder="1000" />
        </label>
        <button className="button" type="submit" disabled={loadingListings}>Apply filters</button>
      </form>

      <section className="listings-page__results" aria-label="Product listings" aria-live="polite">
        {loadingListings ? <p role="status">Loading product listings…</p> : null}
        {!loadingListings && listings.length === 0 && !listingError ? <p className="muted">No matching product listings yet.</p> : null}
        {listingError ? <p role="alert">{listingError}</p> : null}
        {listings.slice(0, visibleListingCount).map((listing) => (
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
        {listings.length > visibleListingCount || hasMoreOnServer ? (
          <button className="button ghost listings-page__load-more" type="button" disabled={loadingMoreListings} onClick={() => void loadMoreListings()}>
            {loadingMoreListings ? "Loading…" : "Load more listings"}
          </button>
        ) : null}
      </section>
    </div>
  );
}
