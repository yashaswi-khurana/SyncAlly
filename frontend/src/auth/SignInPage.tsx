import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, apiRequest, login } from "../api/client";
import type { InvitationAcceptance, InvitationAcceptanceInput, TokenResponse } from "../api/types";
import { invitationPresentation } from "./invitationPresentation";
import { navigateToDeal, navigateToDeals } from "../router";
import TradeFlowScene from "../deals/TradeFlowScene";

function demoQuickFillEnabled() {
  const appEnvironment = import.meta.env.VITE_APP_ENV?.trim().toLowerCase();
  const supportsDemoAccounts = appEnvironment === "development" || appEnvironment === "test";
  return import.meta.env.VITE_ENABLE_DEMO_QUICK_FILL === "true" && supportsDemoAccounts;
}

interface SignInPageProps {
  onSignIn: (tokens: TokenResponse) => void;
}

interface FieldErrors {
  email?: string;
  password?: string;
}

function getInviteTokenFromHash(): string | null {
  const hash = window.location.hash;
  const rawPath = hash.startsWith("#") ? hash.slice(1) : hash;
  const [, queryString] = rawPath.split("?");
  if (queryString) {
    const params = new URLSearchParams(queryString);
    const token = params.get("token");
    if (token) return token;
  }
  return null;
}

export default function SignInPage({ onSignIn }: SignInPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Counterparty invite state
  const [inviteToken, setInviteToken] = useState<string | null>(getInviteTokenFromHash);
  const [mode, setMode] = useState<"signin" | "invite">(() =>
    getInviteTokenFromHash() ? "invite" : "signin",
  );
  const [inviteEmail, setInviteEmail] = useState("");
  const [invitePassword, setInvitePassword] = useState("");
  const [inviteDisplayName, setInviteDisplayName] = useState("");
  const [inviteOrgName, setInviteOrgName] = useState("");
  const [inviteCountryCode, setInviteCountryCode] = useState("US");
  const currentInviteRef = useRef(inviteToken);
  const intent = invitationPresentation(inviteToken);

  useEffect(() => {
    function onHashChange() {
      const token = getInviteTokenFromHash();
      if (currentInviteRef.current === token) return;
      currentInviteRef.current = token;
      setInviteToken(token);
      setMode(token ? "invite" : "signin");
      setInviteEmail("");
      setInvitePassword("");
      setInviteDisplayName("");
      setInviteOrgName("");
      setInviteCountryCode("US");
      setFieldErrors({});
      setFormError(null);
      setSubmitting(false);
    }
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  function fillDemo(role: "buyer" | "seller") {
    setEmail(`${role}@syncally.demo`);
    setPassword("");
    setFieldErrors({});
    setFormError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors: FieldErrors = {};
    if (email.trim() === "") {
      nextErrors.email = "Email is required.";
    }
    if (password === "") {
      nextErrors.password = "Password is required.";
    }
    setFieldErrors(nextErrors);
    setFormError(null);
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      const tokens = await login(email.trim(), password);
      onSignIn(tokens);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setFormError("Invalid email or password.");
      } else if (caught instanceof ApiError) {
        setFormError(caught.message);
      } else {
        setFormError("Sign in failed. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleInviteSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!inviteToken || submitting || intent.kind === "INVALID") return;
    const acceptingToken = inviteToken;

    const nextErrors: FieldErrors = {};
    if (inviteEmail.trim() === "") {
      nextErrors.email = "Email is required.";
    }
    const passwordLength = Array.from(invitePassword).length;
    if (invitePassword === "") {
      nextErrors.password = "Password is required.";
    } else if (passwordLength < 12) {
      nextErrors.password = "Password must be at least 12 characters.";
    } else if (passwordLength > 128) {
      nextErrors.password = "Password must be at most 128 characters.";
    }

    setFieldErrors(nextErrors);
    setFormError(null);
    if (intent.kind === "COUNTERPARTY" && !inviteOrgName.trim()) {
      setFormError("Your company legal name is required.");
      return;
    }
    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSubmitting(true);
    try {
      const payload: InvitationAcceptanceInput = {
        token: inviteToken,
        email: inviteEmail.trim(),
        password: invitePassword,
        display_name: inviteDisplayName.trim() || undefined,
      };
      // A legal name creates a counterparty organization; team invitees join
      // the inviting organization using the invitation's role instead.
      if (intent.kind !== "TEAM" && inviteOrgName.trim()) {
        payload.organization_legal_name = inviteOrgName.trim();
        payload.country_code = inviteCountryCode.trim().toUpperCase() || "US";
      }

      const res = await apiRequest<InvitationAcceptance>("/invitations/accept", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (currentInviteRef.current !== acceptingToken) return;

      if (res.access_token && res.refresh_token) {
        onSignIn({
          access_token: res.access_token,
          refresh_token: res.refresh_token,
          token_type: (res.token_type as "bearer") || "bearer",
        });
      }
      if (res.deal_id) {
        navigateToDeal(res.deal_id);
      } else {
        navigateToDeals();
      }
    } catch (caught) {
      if (currentInviteRef.current !== acceptingToken) return;
      if (caught instanceof ApiError) {
        setFormError(caught.message);
      } else {
        setFormError("Unable to accept invitation. Please try again.");
      }
    } finally {
      if (currentInviteRef.current === acceptingToken) setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout">
      <header className="auth-masthead">
        <a className="auth-wordmark" href="#/deals" aria-label="SyncAlly home">
          <span className="auth-wordmark__mark" aria-hidden="true">
            <svg viewBox="0 0 28 28" focusable="false">
              <path d="M4 6.5h13.5L24 13v8.5H10.5L4 15z" />
              <path d="M4 6.5 10.5 13v8.5M10.5 13H24" />
            </svg>
          </span>
          <span>SyncAlly</span>
        </a>
        <div className="auth-masthead__note">
          <span className="auth-masthead__index">SA / 01</span>
          <span>TRADE RECORDS, KEPT TOGETHER</span>
        </div>
      </header>

      <section className="auth-hero" aria-labelledby="auth-title">
        <div className="auth-hero__meta">
          <span className="eyebrow">Cross-border trade on autopilot</span>
          <span className="auth-hero__edition">BUYER ↔ SELLER</span>
        </div>
        <h1 id="auth-title">
          Cross-Border Trade<br />
          <span>on Autopilot.</span>
        </h1>
        <p className="auth-hero__lede">
          Turn a buyer and seller conversation into a clear, mutually approved deal—with invoicing
          ready to follow.
        </p>

        <div className="auth-diagram" aria-label="Conversation to suggested facts to owner review">
          <div className="auth-diagram__topline">
            <span>HOW IT WORKS</span>
            <span>01 — 03</span>
          </div>
          <div className="auth-diagram__drawing" aria-hidden="true">
            <TradeFlowScene />
          </div>
          <div className="auth-diagram__labels">
            <div>
              <span>01 / DISCUSS</span>
              <strong>Discuss &amp; Extract Terms</strong>
            </div>
            <div>
              <span>02 / APPROVE</span>
              <strong>Cryptographic Bilateral Approval</strong>
            </div>
            <div>
              <span>03 / INVOICE</span>
              <strong>Automated PayPal Invoicing</strong>
            </div>
          </div>
        </div>
        <div className="auth-hero__footnote">
          <span className="auth-hero__footnote-mark" aria-hidden="true">↳</span>
          <span>Both parties approve the same terms before an invoice is created.</span>
        </div>
        <section className="auth-benefits" aria-labelledby="why-syncally">
          <h2 id="why-syncally">Why SyncAlly</h2>
          <ul>
            <li><strong>Guaranteed consensus</strong><span>One agreed version, approved by both sides.</span></li>
            <li><strong>Private by design</strong><span>Keep internal terms private; share only what the deal needs.</span></li>
            <li><strong>Immutable audit record</strong><span>Every approval stays traceable.</span></li>
          </ul>
        </section>
      </section>

      {mode === "invite" && inviteToken ? (
        <aside className="card auth-card" aria-labelledby="invite-onboarding-heading">
          <div className="auth-card__topline">
            <span className="eyebrow">{intent.kind === "TEAM" ? "Team invitation" : "Counterparty Onboarding"}</span>
            <span className="auth-card__number">01 / 01</span>
          </div>
          <h2 id="invite-onboarding-heading">{intent.kind === "TEAM" ? "Join your team." : "Join via counterparty invite."}</h2>
          <p className="auth-card__intro">
            Create your account and register your organization to immediately access the invited deal.
          </p>
          <form className="form" onSubmit={handleInviteSubmit} noValidate>
            {intent.recipientEmail ? <p>Addressed to {intent.recipientEmail}</p> : null}
            {intent.kind === "INVALID" ? <p role="alert">Invalid invitation token</p> : null}
            <div className="field">
              <label htmlFor="invite-email">Email</label>
              <input
                id="invite-email"
                name="email"
                type="email"
                autoComplete="email"
                maxLength={320}
                value={inviteEmail}
                aria-invalid={fieldErrors.email ? true : undefined}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
              {fieldErrors.email ? (
                <p className="field-error" role="alert">
                  {fieldErrors.email}
                </p>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="invite-password">Password (12–128 characters)</label>
              <input
                id="invite-password"
                name="password"
                type="password"
                autoComplete="new-password"
                value={invitePassword}
                aria-invalid={fieldErrors.password ? true : undefined}
                onChange={(e) => setInvitePassword(e.target.value)}
              />
              {fieldErrors.password ? (
                <p className="field-error" role="alert">
                  {fieldErrors.password}
                </p>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="invite-display-name">Your Name</label>
              <input
                id="invite-display-name"
                name="displayName"
                type="text"
                autoComplete="name"
                maxLength={200}
                placeholder="e.g. Kenji Sato"
                value={inviteDisplayName}
                onChange={(e) => setInviteDisplayName(e.target.value)}
              />
            </div>
            {intent.kind !== "TEAM" ? <div className="field">
              <label htmlFor="invite-org-name">{intent.kind === "COUNTERPARTY" ? "Company Legal Name" : "Company Legal Name (Optional)"}</label>
              <input
                id="invite-org-name"
                name="orgName"
                type="text"
                maxLength={200}
                placeholder="e.g. Tokyo Exporters Ltd"
                value={inviteOrgName}
                onChange={(e) => setInviteOrgName(e.target.value)}
              />
            </div> : null}
            {intent.kind !== "TEAM" ? <div className="field">
              <label htmlFor="invite-country-code">Country Code (2 letters)</label>
              <input
                id="invite-country-code"
                name="countryCode"
                type="text"
                maxLength={2}
                placeholder="JP"
                value={inviteCountryCode}
                onChange={(e) => setInviteCountryCode(e.target.value.toUpperCase())}
              />
            </div> : null}
            {formError ? (
              <p className="form-error" role="alert">
                {formError}
              </p>
            ) : null}
            <button type="submit" className="button auth-card__submit" disabled={submitting || intent.kind === "INVALID"}>
              <span>{submitting ? "Joining deal…" : intent.kind === "TEAM" ? "Accept team invitation" : "Create Account & Join Deal"}</span>
              <span aria-hidden="true">↗</span>
            </button>
            <div style={{ marginTop: 12, textAlign: "center" }}>
              <button
                type="button"
                className="button ghost"
                style={{ fontSize: "0.85rem" }}
                onClick={() => setMode("signin")}
              >
                Already have an account? Sign in
              </button>
            </div>
          </form>
          <div className="auth-card__fineprint">
            <span className="auth-card__fineprint-dot" aria-hidden="true" />
            <span>Single-use invitation · auto-linked to trade room</span>
          </div>
        </aside>
      ) : (
        <aside className="card auth-card" aria-labelledby="sign-in-heading">
          <div className="auth-card__topline">
            <span className="eyebrow">Workspace access</span>
            <span className="auth-card__number">01 / 01</span>
          </div>
          <h2 id="sign-in-heading">Open your trade desk.</h2>
          <p className="auth-card__intro">
            Sign in with a provisioned buyer or seller account. Public registration is turned off.
          </p>
          <form className="form" onSubmit={handleSubmit} noValidate>
            {demoQuickFillEnabled() ? (
              <div className="auth-demo-fill" aria-label="Quick-fill demo accounts">
                <span>TRY THE LOCAL DEMO</span>
                <div>
                  <button type="button" onClick={() => fillDemo("buyer")}>Demo Buyer</button>
                  <button type="button" onClick={() => fillDemo("seller")}>Demo Seller</button>
                </div>
                <small>Enter the password configured for your local demo account.</small>
              </div>
            ) : null}
            <div className="field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="username"
                value={email}
                aria-invalid={fieldErrors.email ? true : undefined}
                onChange={(event) => setEmail(event.target.value)}
              />
              {fieldErrors.email ? (
                <p className="field-error" role="alert">
                  {fieldErrors.email}
                </p>
              ) : null}
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                aria-invalid={fieldErrors.password ? true : undefined}
                onChange={(event) => setPassword(event.target.value)}
              />
              {fieldErrors.password ? (
                <p className="field-error" role="alert">
                  {fieldErrors.password}
                </p>
              ) : null}
            </div>
            {formError ? (
              <p className="form-error" role="alert">
                {formError}
              </p>
            ) : null}
            <button type="submit" className="button auth-card__submit" disabled={submitting}>
              <span>{submitting ? "Signing in…" : "Enter workspace"}</span>
              <span aria-hidden="true">↗</span>
            </button>
            {inviteToken ? (
              <div style={{ marginTop: 12, textAlign: "center" }}>
                <button
                  type="button"
                  className="button ghost"
                  style={{ fontSize: "0.85rem" }}
                  onClick={() => setMode("invite")}
                >
                  ← Return to Invitation Sign-up
                </button>
              </div>
            ) : null}
          </form>
          <div className="auth-card__fineprint">
            <span className="auth-card__fineprint-dot" aria-hidden="true" />
            <span>Development accounts · records saved to the local database</span>
          </div>
        </aside>
      )}

      <footer className="auth-footer">
        <span>SYNCALLY / DEAL WORKSPACE</span>
        <span>NEGOTIATE &nbsp;·&nbsp; RECORD &nbsp;·&nbsp; REVIEW</span>
        <span>PRIVATE BY DEFAULT</span>
      </footer>
    </main>
  );
}
