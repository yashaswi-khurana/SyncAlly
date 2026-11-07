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
import {
  navigateToCreateDeal,
  navigateToDeal,
  navigateToDeals,
  navigateToOrganizations,
  navigateToPlatform,
} from "./router";
import DevRoleSwitcher from "./ui/DevRoleSwitcher";
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
  }

  function handleDealCreated(dealId: string, draft?: OpeningMessageDraftInput) {
    if (!currentSessionKey || sessionRef.current !== currentSessionKey || getAccessToken() !== accessToken) return;
    if (draft?.body.trim()) {
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
    if (route.name === "organizationSignup") {
      return <OrganizationSignupPage onSignIn={handleSignIn} />;
    }
    return <SignInPage onSignIn={handleSignIn} />;
  }

  const isCreate = route.name === "create";
  const isOrganizations = route.name === "organizations";
  const isPlatform = route.name === "platform";
  const isWorkspace = route.name === "deals" || route.name === "deal";
  const hasPendingInvitation =
    route.name === "organizations" && Boolean(route.inviteToken);
  const needsOrganizationInvitation = organizations !== null && organizations.length === 0 &&
    !hasPendingInvitation && !isPlatform && route.name !== "organizations";

  return (
    <div className="app-shell">
      <header className="site-nav">
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
        <nav className="site-nav__links" aria-label="Primary">
          <button
            type="button"
            className={`nav-link${isWorkspace ? " is-active" : ""}`}
            onClick={navigateToDeals}
          >
            Workspace
          </button>
          <button
            type="button"
            className={`nav-link${isCreate ? " is-active" : ""}`}
            onClick={navigateToCreateDeal}
          >
            New deal
          </button>
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
        </nav>
        <div className="site-nav__meta">
          <span className="site-nav__environment">LOCAL DEMO</span>
          <button type="button" className="button ghost" onClick={handleSignOut}>
            Sign out
          </button>
        </div>
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
          />
        ) : route.name === "organizations" ? (
          <OrganizationsSettingsPage onAccepted={handleInvitationAccepted} />
        ) : route.name === "platform" ? (
          isSystemAdmin ? <PlatformOrganizationsPage /> : <p role="status">Loading platform access…</p>
        ) : needsOrganizationInvitation ? (
          <section className="card org-access-required" role="status">
            <span className="eyebrow">Organization access</span>
            <h1>Your workspace is waiting for an invitation.</h1>
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
        </div>
      </footer>
      <DevRoleSwitcher onSessionChanged={refreshSessionView} />

      {toast && (
        <aside
          className="onboarding-toast"
          role="status"
          aria-live="polite"
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 1100,
            maxWidth: "420px",
            padding: "12px 18px",
            borderRadius: "8px",
            background: "var(--surface)",
            border: "1px solid var(--accent)",
            color: "var(--ink)",
            boxShadow: "0 12px 36px rgba(0, 0, 0, 0.25)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span
              aria-hidden="true"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: "20px",
                height: "20px",
                borderRadius: "50%",
                background: "rgba(56, 211, 159, 0.2)",
                color: "#38d39f",
                fontWeight: "bold",
                fontSize: "12px",
              }}
            >
              ✓
            </span>
            <span>{toast}</span>
          </div>
          <button
            type="button"
            className="button ghost"
            onClick={() => setToast(null)}
            aria-label="Dismiss notification"
            style={{
              padding: "4px 8px",
              fontSize: "12px",
              border: "none",
              cursor: "pointer",
            }}
          >
            ✕
          </button>
        </aside>
      )}
    </div>
  );
}
