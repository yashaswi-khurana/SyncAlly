import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, login } from "../api/client";
import type { TokenResponse } from "../api/types";
import CustomCursor from "../ui/CustomCursor";
import LiveClock from "../ui/LiveClock";
import Marquee from "../ui/Marquee";
import Reveal from "../ui/Reveal";

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
      <div className="aurora" aria-hidden="true">
        <span className="aurora__blob aurora__blob--a" />
        <span className="aurora__blob aurora__blob--b" />
      </div>
      <CustomCursor />

      <Reveal className="auth-hero">
        <span className="eyebrow">Deal workspace</span>
        <h1 className="display">
          Conversations become{" "}
          <span className="gradient-text">committed agreements</span>.
        </h1>
        <p className="hero__lede">
          SyncAlly turns buyer and seller talks into reviewed trade terms, bilateral approval, and
          durable payment requests — with every decision recorded.
        </p>
        <div className="auth-badges">
          <span className="pill">Bilateral approval</span>
          <span className="pill">Canonical terms</span>
          <span className="pill">Durable payment intent</span>
        </div>
        <div className="hero__marquee">
          <Marquee speed={30}>
            <span>NEGOTIATE</span>
            <span>AGREE</span>
            <span>FULFIL</span>
            <span>PAY</span>
          </Marquee>
        </div>
        <LiveClock />
      </Reveal>

      <Reveal delay={120} className="card auth-card">
        <span className="eyebrow">SyncAlly</span>
        <h2 id="sign-in-heading" style={{ marginTop: 14 }}>
          Sign in to continue
        </h2>
        <p className="muted">
          Use a provisioned demo account. Public registration is not available in this demo.
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
          <button type="submit" className="button" disabled={submitting}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </Reveal>
    </main>
  );
}
