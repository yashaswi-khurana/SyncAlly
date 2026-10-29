import { useState } from "react";
import type { FormEvent } from "react";

import { ApiError, createOrganization, listOrganizations } from "../api/client";
import type { CreateOrganizationInput, Organization } from "../api/types";

import countriesData from "./countries.json";

export interface CountryOption {
  code: string;
  label: string;
}

export const COUNTRY_NAMES: Record<string, string> = countriesData;

export const SUPPORTED_COUNTRIES: readonly CountryOption[] = Object.entries(
  countriesData,
).map(([code, name]) => ({
  code,
  label: name.includes(`(${code})`) ? name : `${name} (${code})`,
}));

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

/**
 * A lost response, timeout, or server error can hide a committed create. Treat
 * only explicit client errors as safe to retry: a 4xx means the server rejected
 * the request before writing anything.
 */
function isAmbiguousCreateFailure(caught: unknown): boolean {
  return !(caught instanceof ApiError) || caught.status === 0 || caught.status >= 500;
}

const UNCONFIRMED_CREATE_MESSAGE =
  "We could not confirm whether your organization was created. Check your connection and try again; we will verify before creating another.";

export default function OnboardingWizard({ onComplete, onSignOut }: OnboardingWizardProps) {
  const [legalName, setLegalName] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [needsReconciliation, setNeedsReconciliation] = useState(false);

  /**
   * The wizard only appears when the account has zero organizations, so any
   * organization found here means an earlier ambiguous attempt already
   * succeeded. Prefer the exact submission, then fall back to the account's
   * organization (the user may have edited the form before retrying).
   */
  async function findExistingOrganization(
    input: CreateOrganizationInput,
  ): Promise<Organization | null> {
    const organizations = await listOrganizations();
    if (organizations.length === 0) {
      return null;
    }
    return (
      organizations.find(
        (organization) =>
          organization.legal_name === input.legal_name &&
          organization.country_code === input.country_code,
      ) ?? organizations[0]
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = legalName.trim();
    const country = countryCode.trim().toUpperCase();

    if (!name) {
      setError("Enter your company legal name.");
      return;
    }

    if (!country || !/^[A-Z]{2}$/.test(country)) {
      setError("Enter a two-letter country code, for example US.");
      return;
    }

    setError(null);
    setIsSubmitting(true);
    const input: CreateOrganizationInput = {
      legal_name: name,
      country_code: country,
    };

    let organizationToDeliver: Organization | null = null;

    try {
      // After an ambiguous failure, never send another create until a fresh
      // read proves the earlier attempt did not commit.
      if (needsReconciliation) {
        let existing: Organization | null = null;
        try {
          existing = await findExistingOrganization(input);
        } catch {
          setError(UNCONFIRMED_CREATE_MESSAGE);
          return;
        }
        if (existing) {
          organizationToDeliver = existing;
        } else {
          setNeedsReconciliation(false);
        }
      }

      if (!organizationToDeliver) {
        try {
          organizationToDeliver = await createOrganization(input);
        } catch (caught) {
          if (isAmbiguousCreateFailure(caught)) {
            // Keep the guard armed even when the read finds nothing: the original
            // request could still commit after this check.
            setNeedsReconciliation(true);
            let existing: Organization | null = null;
            try {
              existing = await findExistingOrganization(input);
            } catch {
              setError(UNCONFIRMED_CREATE_MESSAGE);
              return;
            }
            if (existing) {
              organizationToDeliver = existing;
            } else {
              setError(describeError(caught));
              return;
            }
          } else {
            setError(describeError(caught));
            return;
          }
        }
      }
    } finally {
      setIsSubmitting(false);
    }

    if (organizationToDeliver) {
      try {
        onComplete(organizationToDeliver);
      } catch (callbackError) {
        // Consumer callback errors must be handled separately so they are never
        // displayed as organization-creation failures when creation already succeeded.
        console.error("Error in onComplete callback:", callbackError);
      }
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
            <input
              id="wizard-country-code"
              name="countryCode"
              type="text"
              placeholder="US"
              maxLength={2}
              value={countryCode}
              onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
              disabled={isSubmitting}
              list="wizard-country-suggestions"
            />
            <datalist id="wizard-country-suggestions">
              {SUPPORTED_COUNTRIES.map((country) => (
                <option key={country.code} value={country.code}>
                  {country.label}
                </option>
              ))}
            </datalist>
            <p className="hint">Two-letter ISO country code (e.g. DE, US, GB, ES).</p>
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

