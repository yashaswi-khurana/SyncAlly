export type Route =
  | { name: "deals" }
  | { name: "create" }
  | { name: "deal"; dealId: string }
  | { name: "organizations"; inviteToken?: string; dealId?: string }
  | { name: "invite"; token: string; dealId?: string };

const DEAL_ROUTE = /^\/deals\/([^/]+)$/;
const CREATE_DEAL_PATH = "/deals/new";
const ORGANIZATIONS_PATH = "/settings/organizations";
const INVITE_PATH = "/invite";

export function parseRoute(hash: string): Route {
  const rawPath = hash.startsWith("#") ? hash.slice(1) : hash;
  const [path, queryString] = rawPath.split("?");
  const match = DEAL_ROUTE.exec(path);
  const dealId = match?.[1];
  if (dealId && dealId !== "new") {
    return { name: "deal", dealId: decodeURIComponent(dealId) };
  }
  if (path === CREATE_DEAL_PATH) {
    return { name: "create" };
  }
  if (path === ORGANIZATIONS_PATH || path === `${ORGANIZATIONS_PATH}/`) {
    const params = new URLSearchParams(queryString || "");
    const inviteToken = params.get("token") || undefined;
    const dealIdParam = params.get("dealId") || undefined;
    return { name: "organizations", inviteToken, dealId: dealIdParam };
  }
  if (path === INVITE_PATH || path === `${INVITE_PATH}/`) {
    const params = new URLSearchParams(queryString || "");
    const inviteToken = params.get("token") || "";
    const dealIdParam = params.get("dealId") || undefined;
    return { name: "organizations", inviteToken, dealId: dealIdParam };
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

export function invitePath(token: string, dealId?: string): string {
  const params = new URLSearchParams({ token });
  if (dealId) {
    params.set("dealId", dealId);
  }
  return `#/invite?${params.toString()}`;
}

export function navigateToInvite(token: string, dealId?: string): void {
  window.location.hash = invitePath(token, dealId);
}


