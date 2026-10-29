import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createOrganization } from "../api/client";
import type { Organization } from "../api/types";

export interface CountryOption {
  code: string;
  label: string;
}

export const SUPPORTED_COUNTRIES: readonly CountryOption[] = [
  { code: "DE", label: "Germany (DE)" },
  { code: "US", label: "United States (US)" },
  { code: "GB", label: "United Kingdom (GB)" },
  { code: "CA", label: "Canada (CA)" },
  { code: "FR", label: "France (FR)" },
  { code: "NL", label: "Netherlands (NL)" },
  { code: "CH", label: "Switzerland (CH)" },
  { code: "SG", label: "Singapore (SG)" },
  { code: "AU", label: "Australia (AU)" },
  { code: "JP", label: "Japan (JP)" },
  { code: "IN", label: "India (IN)" },
  { code: "BR", label: "Brazil (BR)" },
] as const;

export interface OnboardingWizardProps {
  onComplete: (organization: Organization) => void;
  onSignOut?: () => void;
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function OnboardingWizard({ onComplete, onSignOut }: OnboardingWizardProps) {
  const [legalName, setLegalName] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = legalName.trim();
    const country = countryCode.trim().toUpperCase();

    if (!name) {
      setError("Enter your company legal name.");
      return;
    }

    if (!country || !/^[A-Z]{2}$/.test(country)) {
      setError("Select a two-letter country code.");
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const created = await createOrganization({
        legal_name: name,
        country_code: country,
      });
      onComplete(created);
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="manual-fact-modal-backdrop" role="presentation">
      <div
        className="manual-fact-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-wizard-title"
      >
        <div className="panel-head">
          <span className="eyebrow">Welcome to SyncAlly / First-run setup</span>
        </div>
        <h2 id="onboarding-wizard-title" className="display" style={{ fontSize: "1.45rem", margin: "8px 0" }}>
          Set up your trading organization
        </h2>
        <p className="muted" style={{ marginBottom: "20px", fontSize: "0.88rem", lineHeight: 1.5 }}>
          Before opening the Deal Register, create your primary trading organization. You will immediately
          be established as its administrator.
        </p>

        <form className="form" onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="wizard-legal-name">Company Legal Name</label>
            <input
              id="wizard-legal-name"
              name="legalName"
              type="text"
              placeholder="Global Grain Importers Ltd"
              value={legalName}
              onChange={(e) => setLegalName(e.target.value)}
              disabled={isSubmitting}
              autoFocus
            />
            <p className="hint">The official registered name of your company or trading firm.</p>
          </div>

          <div className="field">
            <label htmlFor="wizard-country-code">Country Code</label>
            <select
              id="wizard-country-code"
              name="countryCode"
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value)}
              disabled={isSubmitting}
            >
              <option value="">Select country code</option>
              {SUPPORTED_COUNTRIES.map((country) => (
                <option key={country.code} value={country.code}>
                  {country.label}
                </option>
              ))}
            </select>
            <p className="hint">Two-letter ISO country code where your organization is registered.</p>
          </div>

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
              marginTop: "24px",
            }}
          >
            <button type="submit" className="button" disabled={isSubmitting}>
              {isSubmitting ? "Creating organization…" : "Create & continue to Deal Register"}
            </button>
            {onSignOut && (
              <button
                type="button"
                className="button ghost"
                onClick={onSignOut}
                disabled={isSubmitting}
              >
                Sign out
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}

