import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, registerOrganization } from "../api/client";
import type { TokenResponse } from "../api/types";
import { navigateToOrganizations } from "../router";

export default function OrganizationSignupPage({ onSignIn }: {
  onSignIn: (tokens: TokenResponse) => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [legalName, setLegalName] = useState("");
  const [countryCode, setCountryCode] = useState("US");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const cleanName = displayName.trim();
    const cleanEmail = email.trim().toLowerCase();
    const cleanLegalName = legalName.trim();
    const cleanCountryCode = countryCode.trim().toUpperCase();
    if (!cleanName || !cleanEmail || !cleanLegalName) {
      setError("Enter your name, email, and organization legal name.");
      return;
    }
    if (password.length < 12 || Array.from(password).length > 128) {
      setError("Password must be 12–128 characters.");
      return;
    }
    if (!/^[A-Z]{2}$/.test(cleanCountryCode)) {
      setError("Enter a two-letter country code, for example US.");
      return;
    }

    setSubmitting(true);
    try {
      const tokens = await registerOrganization({
        display_name: cleanName,
        email: cleanEmail,
        password,
        legal_name: cleanLegalName,
        country_code: cleanCountryCode,
      });
      onSignIn(tokens);
      navigateToOrganizations();
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message);
      } else {
        setError("We could not create your organization. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-layout org-signup-layout">
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
        <nav className="auth-public-nav" aria-label="Account navigation">
          <span>Already have an account?</span>
          <a className="button secondary" href="#/deals">Sign in</a>
        </nav>
      </header>

      <section className="auth-hero" aria-labelledby="org-signup-title">
        <div className="auth-hero__meta">
          <span className="eyebrow">Start your organization</span>
          <span className="auth-hero__edition">YOUR COMPANY · YOUR TEAM</span>
        </div>
        <h1 id="org-signup-title">Set up your <span>trade desk.</span></h1>
        <p className="auth-hero__lede">
          Create your owner account and company workspace together. You’ll be the first organization administrator.
        </p>
        <div className="auth-hero__footnote">
          <span className="auth-hero__footnote-mark" aria-hidden="true">↳</span>
          <span>After setup, invite teammates from your organization’s Team &amp; access page.</span>
        </div>
      </section>

      <aside className="card auth-card org-signup-card" aria-labelledby="org-signup-card-title">
        <div className="auth-card__topline">
          <span className="eyebrow">Organization onboarding</span>
          <span className="auth-card__number">01 / 01</span>
        </div>
        <h2 id="org-signup-card-title">Create an organization</h2>
        <p className="auth-card__intro">Your account and organization are created together.</p>
        <form className="form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="org-owner-name">Your name</label>
            <input id="org-owner-name" name="display_name" autoComplete="name" maxLength={200}
              value={displayName} onChange={(event) => setDisplayName(event.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label htmlFor="org-owner-email">Work email</label>
            <input id="org-owner-email" name="email" type="email" autoComplete="email" maxLength={320}
              value={email} onChange={(event) => setEmail(event.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label htmlFor="org-owner-password">Password (12–128 characters)</label>
            <input id="org-owner-password" name="password" type="password" autoComplete="new-password"
              value={password} onChange={(event) => setPassword(event.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label htmlFor="org-legal-name">Organization legal name</label>
            <input id="org-legal-name" name="legal_name" autoComplete="organization" maxLength={200}
              placeholder="Northwind Trading Ltd." value={legalName}
              onChange={(event) => setLegalName(event.target.value)} disabled={submitting} />
          </div>
          <div className="field">
            <label htmlFor="org-country-code">Country code</label>
            <input id="org-country-code" name="country_code" autoComplete="country" maxLength={2}
              placeholder="US" value={countryCode}
              onChange={(event) => setCountryCode(event.target.value.toUpperCase())} disabled={submitting} />
            <p className="hint">Two-letter ISO code</p>
          </div>
          {error ? <p className="form-error" role="alert">{error}</p> : null}
          <button type="submit" className="button auth-card__submit" disabled={submitting}>
            <span>{submitting ? "Creating workspace…" : "Create organization"}</span>
            <span aria-hidden="true">↗</span>
          </button>
        </form>
        <div className="auth-card__fineprint">
          <span className="auth-card__fineprint-dot" aria-hidden="true" />
          <span>You become the first administrator of this organization.</span>
        </div>
      </aside>

      <footer className="auth-footer">
        <span>SYNCALLY / DEAL WORKSPACE</span>
        <span>NEGOTIATE &nbsp;·&nbsp; RECORD &nbsp;·&nbsp; REVIEW</span>
        <span>PRIVATE BY DEFAULT</span>
      </footer>
    </main>
  );
}
