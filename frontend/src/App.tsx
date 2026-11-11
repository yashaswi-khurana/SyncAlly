import { useCallback, useEffect, useRef, useState } from "react";

import SignInPage from "./auth/SignInPage";
import { useSession } from "./auth/useSession";
import { useHashRoute } from "./app/useHashRoute";
import { getCurrentUser, listOrganizations } from "./api/client";
import { getAccessToken } from "./api/tokenStore";
import type { InvitationAcceptance, Organization, TokenResponse } from "./api/types";
import CreateDealPage from "./deals/CreateDealPage";
import DealDetailPage from "./deals/DealDetailPage";
import DealsPage from "./deals/DealsPage";
import OrganizationSignupPage from "./organizations/OrganizationSignupPage";
import OrganizationsSettingsPage from "./organizations/OrganizationsSettingsPage";
import PlatformOrganizationsPage from "./platform/PlatformOrganizationsPage";
import MarketplacePage from "./marketplace/MarketplacePage";
import SourcingHubPage from "./sourcing/SourcingHubPage";
import {
  navigateToCreateDeal,
  navigateToDeal,
  navigateToDeals,
  navigateToOrganizations,
  navigateToMarketplace,
  navigateToSourcing,
  navigateToPlatform,
  parseRoute,
} from "./router";
import AmbientField from "./ui/AmbientField";
import CustomCursor from "./ui/CustomCursor";
import DevRoleSwitcher from "./ui/DevRoleSwitcher";
import NavIndicator from "./ui/NavIndicator";
import PhysicsWordmark from "./ui/PhysicsWordmark";
import ScrollProgress from "./ui/ScrollProgress";
import SplitText from "./ui/SplitText";
import type { OpeningMessageDraft, OpeningMessageDraftInput } from "./deals/openingMessageDraft";

export default function App() {
  const { accessToken, signIn, signOut } = useSession();
  const route = useHashRoute();
  const [sessionVersion, setSessionVersion] = useState(0);
  const [sessionGeneration, setSessionGeneration] = useState(0);
  const sessionGenerationRef = useRef(0);
  const [organizations, setOrganizations] = useState<Organization[] | null>(null);
  const [isSystemAdmin, setIsSystemAdmin] = useState<boolean | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [navOpen, setNavOpen] = useState(false);
  const [navRoute, setNavRoute] = useState(route);
  if (navRoute !== route) {
    // close the mobile drawer whenever navigation happens (render-phase
    // adjustment — no effect needed)
    setNavRoute(route);
    setNavOpen(false);
  }
  const [openingMessageDrafts, setOpeningMessageDrafts] = useState<OpeningMessageDraft[]>([]);

  const currentSessionKey = accessToken ? `${accessToken}:${sessionGeneration}` : null;
  const sessionRef = useRef(currentSessionKey);

  const advanceSessionGeneration = useCallback(() => {
    const nextGeneration = sessionGenerationRef.current + 1;
    sessionGenerationRef.current = nextGeneration;
    setSessionGeneration(nextGeneration);
    return nextGeneration;
  }, []);

  useEffect(() => {
    sessionRef.current = currentSessionKey;
  }, [currentSessionKey]);

  useEffect(() => {
    function clearCurrentSession() {
      advanceSessionGeneration();
      sessionRef.current = null;
      setOpeningMessageDrafts([]);
      setOrganizations(null);
      setToast(null);
      signOut();
    }
    function handleExpiredSession(failedToken?: string) {
      if (!failedToken || (
        getAccessToken() !== failedToken ||
        sessionRef.current !== `${failedToken}:${sessionGeneration}`
      )) {
        return;
      }
      clearCurrentSession();
    }
    function handleSessionExpired(event: Event) {
      const failedToken = (event as CustomEvent<{ token?: string }>).detail?.token;
      handleExpiredSession(failedToken);
    }
    function handleStorageChange(event: StorageEvent) {
      if (event.key === "syncally.accessToken" && event.newValue === null && accessToken && getAccessToken() === null) {
        if (sessionRef.current === `${accessToken}:${sessionGeneration}`) {
          clearCurrentSession();
        }
      }
    }
    window.addEventListener("syncally:session-expired", handleSessionExpired);
    window.addEventListener("storage", handleStorageChange);
    return () => {
      window.removeEventListener("syncally:session-expired", handleSessionExpired);
      window.removeEventListener("storage", handleStorageChange);
    };
  }, [accessToken, advanceSessionGeneration, sessionGeneration, sessionVersion, signOut]);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    void (async () => {
      try {
        const [orgResult, userResult] = await Promise.allSettled([listOrganizations(), getCurrentUser()]);
        if (!cancelled) {
          setOrganizations(orgResult.status === "fulfilled" ? orgResult.value : null);
          setIsSystemAdmin(userResult.status === "fulfilled" && userResult.value.system_role === "SYSTEM_ADMIN");
        }
      } catch {
        if (!cancelled) setOrganizations(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [accessToken, sessionVersion]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => {
      setToast(null);
    }, 6000);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (route.name === "platform" && isSystemAdmin === false) navigateToDeals();
  }, [route.name, isSystemAdmin]);

  useEffect(() => {
    if (accessToken && route.name === "organizationSignup") navigateToOrganizations();
  }, [accessToken, route.name]);

  function refreshSessionView() {
    advanceSessionGeneration();
    sessionRef.current = null;
    setOpeningMessageDrafts([]);
    navigateToDeals();
    setSessionVersion((version) => version + 1);
  }

  function handleSignOut() {
    advanceSessionGeneration();
    sessionRef.current = null;
    setOpeningMessageDrafts([]);
    setOrganizations(null);
    setIsSystemAdmin(null);
    setToast(null);
    signOut();
  }

  function handleSignIn(tokens: TokenResponse) {
    const nextGeneration = advanceSessionGeneration();
    sessionRef.current = `${tokens.access_token}:${nextGeneration}`;
    setOpeningMessageDrafts([]);
    setOrganizations(null);
    setIsSystemAdmin(null);
    signIn(tokens);
    // A fresh sign-in must not inherit the previous session's settings route.
    // Deep links survive: create/deal routes, organization signup, and any
    // route carrying an invitation token (`/invite?token=…`, `?token=…`).
    const current = parseRoute(window.location.hash);
    if (current.name === "organizations" && !current.inviteToken) {
      navigateToDeals();
    }
  }

  function handleDealCreated(dealId: string, draft?: OpeningMessageDraftInput | { text: string; source: string }) {
    if (!currentSessionKey || sessionRef.current !== currentSessionKey || getAccessToken() !== accessToken) return;
    if (draft && "body" in draft && draft.body.trim()) {
      const openingMessageDraft = { ...draft, dealId };
      setOpeningMessageDrafts((current) => [
        ...current.filter((item) => item.dealId !== dealId || item.organizationId !== draft.organizationId),
        openingMessageDraft,
      ]);
    }
    navigateToDeal(dealId);
  }

  function handleOpeningMessageDraftReady(dealId: string, draft: OpeningMessageDraftInput) {
    if (!currentSessionKey || sessionRef.current !== currentSessionKey || getAccessToken() !== accessToken) return;
    const openingMessageDraft = { ...draft, dealId };
    setOpeningMessageDrafts((current) => [
      ...current.filter((item) => item.dealId !== dealId || item.organizationId !== draft.organizationId),
      openingMessageDraft,
    ]);
  }

  const handleOpeningMessageDraftChange = useCallback((draft: OpeningMessageDraft) => {
    setOpeningMessageDrafts((current) => current.map((item) =>
      item.dealId === draft.dealId && item.organizationId === draft.organizationId
        ? draft
        : item,
    ));
  }, []);

  const handleOpeningMessageDraftComplete = useCallback((dealId: string, organizationId: string) => {
    setOpeningMessageDrafts((current) => current.filter((item) =>
      item.dealId !== dealId || item.organizationId !== organizationId,
    ));
  }, []);

  async function handleInvitationAccepted(
    result: InvitationAcceptance,
    isCurrentInvitation: () => boolean,
  ) {
    if (!currentSessionKey || sessionRef.current !== currentSessionKey ||
        getAccessToken() !== accessToken || !isCurrentInvitation()) return;
    setOrganizations(null);
    let acceptedToken = accessToken;
    if (result.access_token && result.refresh_token) {
      acceptedToken = result.access_token;
      handleSignIn({ access_token: result.access_token, refresh_token: result.refresh_token,
        token_type: result.token_type ?? "bearer" });
    }
    const acceptedSession = sessionRef.current;
    const refreshed = await listOrganizations();
    if (sessionRef.current !== acceptedSession || getAccessToken() !== acceptedToken ||
      !isCurrentInvitation()) return;
    setOrganizations(refreshed);
    if (result.deal_id) navigateToDeal(result.deal_id);
    else navigateToDeals();
  }

  if (!accessToken) {
    return (
      <>
        {route.name === "organizationSignup" ? (
          <OrganizationSignupPage onSignIn={handleSignIn} />
        ) : (
          <SignInPage onSignIn={handleSignIn} />
        )}
        <CustomCursor />
      </>
    );
  }

  // const isCreate = route.name === "create";
  const isOrganizations = route.name === "organizations";
  const isMarketplace = route.name === "marketplace";
  const isSourcing = route.name === "sourcing";
  const isPlatform = route.name === "platform";
  const isWorkspace = route.name === "deals" || route.name === "deal";
  const hasPendingInvitation =
    route.name === "organizations" && Boolean(route.inviteToken);
  const needsOrganizationInvitation = organizations !== null && organizations.length === 0 &&
    !hasPendingInvitation && !isPlatform && route.name !== "organizations" && !isMarketplace && !isSourcing;

  // presentation only: restarts the page-change flash and re-places the nav pill
  const viewKey = route.name === "deal" ? `deal:${route.dealId}` : route.name;

  return (
    <div className="app-shell">
      <AmbientField />
      <ScrollProgress />
      <span key={viewKey} className="route-flash" aria-hidden="true" />
      <header className={`site-nav${navOpen ? " is-open" : ""}`}>
        <button type="button" className="brand" onClick={navigateToDeals}>
          <span className="brand__mark" aria-hidden="true">
            <svg viewBox="0 0 28 28" focusable="false">
              <path d="M4 6.5h13.5L24 13v8.5H10.5L4 15z" />
              <path d="M4 6.5 10.5 13v8.5M10.5 13H24" />
            </svg>
          </span>
          <span className="brand__type">
            <span>SyncAlly</span>
            <small>TRADE FOLIO</small>
          </span>
        </button>
        <div className="site-nav__meta">
          {import.meta.env.DEV ? <span className="site-nav__environment">LOCAL DEMO</span> : null}
        </div>
        <nav id="primary-nav" className="site-nav__links" aria-label="Primary" onClick={() => setNavOpen(false)}>
          <NavIndicator layoutKey={`${viewKey}:${isSystemAdmin ? "admin" : "member"}:${navOpen ? "open" : "closed"}`} />
          <button
            type="button"
            className={`nav-link${isWorkspace ? " is-active" : ""}`}
            onClick={navigateToDeals}
          >
            Workspace
          </button>
          <button
            type="button"
            className={`nav-link${isMarketplace ? " is-active" : ""}`}
            onClick={navigateToMarketplace}
          >
            Marketplace
          </button>
          <button
            type="button"
            className={`nav-link${isSourcing ? " is-active" : ""}`}
            onClick={() => navigateToSourcing()}
          >
            Sourcing Hub
          </button>
          {/* <button
            type="button"
            className={`nav-link${isCreate ? " is-active" : ""}`}
            onClick={() => navigateToCreateDeal()}
          >
            New deal
          </button> */}
          <button
            type="button"
            className={`nav-link${isOrganizations ? " is-active" : ""}`}
            onClick={navigateToOrganizations}
          >
            Organizations
          </button>
          {isSystemAdmin ? (
            <button
              type="button"
              className={`nav-link${isPlatform ? " is-active" : ""}`}
              onClick={navigateToPlatform}
            >
              Platform admin
            </button>
          ) : null}
          <button type="button" className="button secondary nav-signout" onClick={handleSignOut}>
            Sign out
          </button>
        </nav>
        <button
          type="button"
          className="site-nav__toggle"
          aria-expanded={navOpen}
          aria-controls="primary-nav"
          aria-label={navOpen ? "Close menu" : "Open menu"}
          onClick={() => setNavOpen((open) => !open)}
        >
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            {navOpen ? <path d="M4 4 14 14 M14 4 4 14" /> : <path d="M3 5h12 M3 9h12 M3 13h12" />}
          </svg>
        </button>
      </header>

      <main className="app-main" key={sessionVersion}>
        {route.name === "deal" ? (
          <DealDetailPage
            key={route.dealId}
            dealId={route.dealId}
            onBackToDeals={navigateToDeals}
            openingMessageDraft={openingMessageDrafts.find((draft) => draft.dealId === route.dealId)}
            onOpeningMessageDraftChange={handleOpeningMessageDraftChange}
            onOpeningMessageDraftComplete={handleOpeningMessageDraftComplete}
          />
        ) : route.name === "create" ? (
          <CreateDealPage
            onCreated={handleDealCreated}
            onOpeningMessageDraftReady={handleOpeningMessageDraftReady}
            initialCounterpartyId={route.sellerOrganizationId}
            initialInitiatorParty={route.initiatorParty}
            initialRfqId={route.rfqId}
            initialListingId={route.listingId}
          />
        ) : route.name === "marketplace" ? (
          <MarketplacePage organizations={organizations ?? []} />
        ) : route.name === "sourcing" ? (
          <SourcingHubPage
            organizations={organizations ?? []}
            initialListingId={route.listingId}
          />
        ) : route.name === "organizations" ? (
          <OrganizationsSettingsPage onAccepted={handleInvitationAccepted} />
        ) : route.name === "platform" ? (
          isSystemAdmin ? (
            <PlatformOrganizationsPage />
          ) : (
            <>
              <p role="status">Loading platform access…</p>
              <div className="skeleton-stack" aria-hidden="true">
                <span className="skeleton-bar skeleton-bar--mid" />
                <span className="skeleton-bar" />
                <span className="skeleton-bar skeleton-bar--short" />
              </div>
            </>
          )
        ) : needsOrganizationInvitation ? (
          <section className="card org-access-required" role="status">
            <span className="eyebrow">Organization access</span>
            <h1><SplitText text="Your workspace is waiting for an invitation." /></h1>
            <p>Your account is not a member of an organization yet. Ask an organization administrator to invite you.</p>
            <div className="org-access-required__actions">
              <button type="button" className="button" onClick={handleSignOut}>Sign out</button>
            </div>
          </section>
        ) : (
          <DealsPage onOpenDeal={navigateToDeal} onCreateDeal={navigateToCreateDeal} />
        )}
      </main>

      <footer className="site-footer">
        <div className="site-footer__inner">
          <div className="site-footer__row">
            <span>SYNCALLY / SHARED TRADE RECORD</span>
            <span>Every reviewed term stays tied to its source.</span>
          </div>
          <PhysicsWordmark text="SyncAlly" className="site-footer__wordmark" />
        </div>
      </footer>
      <DevRoleSwitcher onSessionChanged={refreshSessionView} />
      <CustomCursor />

      {toast && (
        <aside className="onboarding-toast" role="status" aria-live="polite">
          <div className="onboarding-toast__message">
            <svg
              className="onboarding-toast__icon"
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M3 8.5 6.5 12 13 4.5" />
            </svg>
            <span>{toast}</span>
          </div>
          <button
            type="button"
            className="button ghost onboarding-toast__dismiss"
            onClick={() => setToast(null)}
            aria-label="Dismiss notification"
          >
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <path d="M3 3 9 9 M9 3 3 9" />
            </svg>
          </button>
        </aside>
      )}
    </div>
  );
}
