export type Route =
  | { name: "deals" }
  | { name: "create" }
  | { name: "deal"; dealId: string }
  | { name: "organizations" };

const DEAL_ROUTE = /^\/deals\/([^/]+)$/;
const CREATE_DEAL_PATH = "/deals/new";
const ORGANIZATIONS_PATH = "/settings/organizations";

export function parseRoute(hash: string): Route {
  const rawPath = hash.startsWith("#") ? hash.slice(1) : hash;
  const path = rawPath.split("?")[0];
  const match = DEAL_ROUTE.exec(path);
  const dealId = match?.[1];
  if (dealId && dealId !== "new") {
    return { name: "deal", dealId: decodeURIComponent(dealId) };
  }
  if (path === CREATE_DEAL_PATH) {
    return { name: "create" };
  }
  if (path === ORGANIZATIONS_PATH || path === `${ORGANIZATIONS_PATH}/`) {
    return { name: "organizations" };
  }
  return { name: "deals" };
}

export function dealPath(dealId: string): string {
  return `#/deals/${encodeURIComponent(dealId)}`;
}

export function navigateToDeal(dealId: string): void {
  window.location.hash = dealPath(dealId);
}

export function navigateToDeals(): void {
  window.location.hash = "#/deals";
}

export function navigateToCreateDeal(): void {
  window.location.hash = `#${CREATE_DEAL_PATH}`;
}

export function organizationsPath(): string {
  return `#${ORGANIZATIONS_PATH}`;
}

export function navigateToOrganizations(): void {
  window.location.hash = organizationsPath();
}

