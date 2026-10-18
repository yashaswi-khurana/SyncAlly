export type Route =
  | { name: "deals" }
  | { name: "create" }
  | { name: "deal"; dealId: string };

const DEAL_ROUTE = /^\/deals\/([^/]+)$/;
const CREATE_DEAL_PATH = "/deals/new";

export function parseRoute(hash: string): Route {
  const path = hash.startsWith("#") ? hash.slice(1) : hash;
  const match = DEAL_ROUTE.exec(path);
  const dealId = match?.[1];
  if (dealId && dealId !== "new") {
    return { name: "deal", dealId: decodeURIComponent(dealId) };
  }
  if (path === CREATE_DEAL_PATH) {
    return { name: "create" };
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
