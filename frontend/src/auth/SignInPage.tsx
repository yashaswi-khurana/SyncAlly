import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, login } from "../api/client";
import type { TokenResponse } from "../api/types";
import TradeFlowScene from "../deals/TradeFlowScene";

interface SignInPageProps {
  onSignIn: (tokens: TokenResponse) => void;
}

interface FieldErrors {
  email?: string;
  password?: string;
}

export default function SignInPage({ onSignIn }: SignInPageProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

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
          <span className="eyebrow">A shared record for both sides</span>
          <span className="auth-hero__edition">BUYER ↔ SELLER</span>
        </div>
        <h1 id="auth-title">
          When terms matter,<br />
          <span>keep the whole conversation.</span>
        </h1>
        <p className="auth-hero__lede">
          Read the conversation alongside source-linked facts. Each organization reviews the facts
          it owns, with private details kept to that side.
        </p>

        <div className="auth-diagram" aria-label="Conversation to suggested facts to owner review">
          <div className="auth-diagram__topline">
            <span>THE RECORD PATH</span>
            <span>01 — 03</span>
          </div>
          <div className="auth-diagram__drawing" aria-hidden="true">
            <TradeFlowScene />
          </div>
          <div className="auth-diagram__labels">
            <div>
              <span>01 / INPUT</span>
              <strong>Conversation</strong>
            </div>
            <div>
              <span>02 / RECORD</span>
              <strong>Suggested facts</strong>
            </div>
            <div>
              <span>03 / REVIEW</span>
              <strong>Owner review</strong>
            </div>
          </div>
        </div>
        <div className="auth-hero__footnote">
          <span className="auth-hero__footnote-mark" aria-hidden="true">↳</span>
          <span>Reviewing a fact records a decision; it does not commit an agreement.</span>
        </div>
      </section>

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
        </form>
        <div className="auth-card__fineprint">
          <span className="auth-card__fineprint-dot" aria-hidden="true" />
          <span>Development accounts · records saved to the local database</span>
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
