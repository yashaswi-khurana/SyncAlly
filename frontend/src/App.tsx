import { useEffect, useRef, useState } from "react";

import SignInPage from "./auth/SignInPage";
import { useSession } from "./auth/useSession";
import { useHashRoute } from "./app/useHashRoute";
import { listOrganizations } from "./api/client";
import type { Organization } from "./api/types";
import CreateDealPage from "./deals/CreateDealPage";
import DealDetailPage from "./deals/DealDetailPage";
import DealsPage from "./deals/DealsPage";
import OnboardingWizard from "./organizations/OnboardingWizard";
import OrganizationsSettingsPage from "./organizations/OrganizationsSettingsPage";
import {
  navigateToCreateDeal,
  navigateToDeal,
  navigateToDeals,
  navigateToOrganizations,
} from "./router";
import DevRoleSwitcher from "./ui/DevRoleSwitcher";

export default function App() {
  const { accessToken, signIn, signOut } = useSession();
  const route = useHashRoute();
  const [sessionVersion, setSessionVersion] = useState(0);
  const [organizations, setOrganizations] = useState<Organization[] | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const currentSessionKey = accessToken ? `${accessToken}:${sessionVersion}` : null;
  const sessionRef = useRef(currentSessionKey);

  useEffect(() => {
    sessionRef.current = currentSessionKey;
  }, [currentSessionKey]);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    void (async () => {
      try {
        const orgs = await listOrganizations();
        if (!cancelled) {
          setOrganizations(orgs);
        }
      } catch {
        if (!cancelled) {
          setOrganizations(null);
        }
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

  function handleOrganizationCreated(created: Organization, sessionAtStart: string | null) {
    if (!sessionRef.current || sessionRef.current !== sessionAtStart) {
      return;
    }
    setOrganizations((prev) => (prev ? [...prev, created] : [created]));
    navigateToDeals();
    setToast(`Created ${created.legal_name} (${created.country_code}). Welcome to the Deal Register!`);
  }

  function refreshSessionView() {
    navigateToDeals();
    setSessionVersion((version) => version + 1);
  }

  function handleSignOut() {
    sessionRef.current = null;
    setOrganizations(null);
    setToast(null);
    signOut();
  }

  if (!accessToken) {
    return <SignInPage onSignIn={signIn} />;
  }

  const isCreate = route.name === "create";
  const isOrganizations = route.name === "organizations";
  const isWorkspace = route.name === "deals" || route.name === "deal";
  const hasPendingInvitation =
    route.name === "organizations" && Boolean(route.inviteToken);
  const hasZeroOrganizations = Boolean(organizations !== null && organizations.length === 0);

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
          />
        ) : route.name === "create" ? (
          <CreateDealPage onCreated={navigateToDeal} />
        ) : route.name === "organizations" ? (
          <OrganizationsSettingsPage />
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

      {hasZeroOrganizations && !hasPendingInvitation && (
        <OnboardingWizard
          key={currentSessionKey ?? "none"}
          onComplete={(created) => handleOrganizationCreated(created, currentSessionKey)}
          onSignOut={handleSignOut}
        />
      )}

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
