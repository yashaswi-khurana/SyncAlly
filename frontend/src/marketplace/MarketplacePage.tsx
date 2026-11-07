import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, searchOrganizationDirectory } from "../api/client";
import type { Organization, OrganizationDirectoryItem, OrganizationDirectorySearch } from "../api/types";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setFilters({
      q: name.trim() || undefined,
      product: product.trim() || undefined,
      country_code: country.trim().toUpperCase() || undefined,
      capability: capability.trim() || undefined,
    });
  }

  const ownOrganizationIds = new Set(organizations.map((organization) => organization.id));

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
