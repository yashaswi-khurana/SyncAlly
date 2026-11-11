import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import { ApiError, getOrganizationProfile, updateOrganizationProfile } from "../api/client";
import type { ContactVisibility, Organization, OrganizationContact, OrganizationProfile } from "../api/types";

interface Props {
  organization: Organization;
}

function describeError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.status === 401) {
      return "Your session has expired. Sign in again.";
    }
    return caught.message;
  }
  if (caught instanceof Error && caught.message) {
    return caught.message;
  }
  return "Something went wrong. Please try again.";
}

export default function OrganizationProfileSection({ organization }: Props) {
  const isAdmin = organization.role === "ADMIN";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<OrganizationProfile | null>(null);
  const [reloadCount, setReloadCount] = useState(0);

  // Edit state
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);

  // Form draft state
  const [capabilitiesDraft, setCapabilitiesDraft] = useState("");
  const [productsDraft, setProductsDraft] = useState("");
  const [regionsDraft, setRegionsDraft] = useState("");
  const [contactsDraft, setContactsDraft] = useState<OrganizationContact[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await getOrganizationProfile(organization.id);
        if (!cancelled) {
          setProfile(data);
          setError(null);
          setIsStale(false);
          setIsEditing(false);
          setSaveError(null);
          setLoading(false);
        }
      } catch (caught) {
        if (!cancelled) {
          setError(describeError(caught));
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [organization.id, reloadCount]);

  function refreshProfile() {
    setLoading(true);
    setReloadCount((c) => c + 1);
  }

  function startEditing() {
    if (!profile) return;
    setCapabilitiesDraft(profile.capabilities.join(", "));
    setProductsDraft(profile.products.join(", "));
    setRegionsDraft(profile.regions.join(", "));
    setContactsDraft(
      profile.contacts.map((c) => ({
        ...c,
        consent_obtained: c.consent_obtained ?? true,
      })),
    );
    setSaveError(null);
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
    setSaveError(null);
    setIsStale(false);
  }

  function handleAddContact() {
    setContactsDraft((current) => [
      ...current,
      {
        name: "",
        purpose: "",
        consent_obtained: true,
        visibility: "PRIVATE" as ContactVisibility,
        role_title: "",
        email: "",
        phone: "",
      },
    ]);
  }

  function handleRemoveContact(index: number) {
    setContactsDraft((current) => current.filter((_, i) => i !== index));
  }

  function handleContactChange(index: number, field: keyof OrganizationContact, value: unknown) {
    setContactsDraft((current) =>
      current.map((c, i) => (i === index ? { ...c, [field]: value } : c)),
    );
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;

    const capabilities = capabilitiesDraft
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    const products = productsDraft
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    const regions = regionsDraft
      .split(",")
      .map((s) => s.trim().toUpperCase())
      .filter((s) => s.length > 0);

    for (const cap of capabilities) {
      if (cap.length > 200) {
        setSaveError(`Capability "${cap.slice(0, 20)}..." exceeds 200 characters.`);
        return;
      }
    }
    for (const prod of products) {
      if (prod.length > 200) {
        setSaveError(`Product "${prod.slice(0, 20)}..." exceeds 200 characters.`);
        return;
      }
    }

    for (let i = 0; i < contactsDraft.length; i++) {
      const c = contactsDraft[i];
      if (!c.name.trim()) {
        setSaveError(`Contact #${i + 1} requires a name.`);
        return;
      }
      if (!c.purpose.trim()) {
        setSaveError(`Contact #${i + 1} requires a purpose.`);
        return;
      }
      if (!c.email?.trim() && !c.phone?.trim()) {
        setSaveError(`Contact #${i + 1} requires at least an email or phone number.`);
        return;
      }
    }

    setSaving(true);
    setSaveError(null);
    setIsStale(false);

    try {
      const updated = await updateOrganizationProfile(organization.id, {
        expected_version: profile.version,
        capabilities,
        products,
        regions,
        contacts: contactsDraft.map((c) => ({
          ...c,
          name: c.name.trim(),
          purpose: c.purpose.trim(),
          role_title: c.role_title?.trim() || null,
          email: c.email?.trim() || null,
          phone: c.phone?.trim() || null,
        })),
      });
      setProfile(updated);
      setIsEditing(false);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 409) {
        setIsStale(true);
        setSaveError("Profile version conflict: the profile was updated elsewhere. Please refresh.");
      } else {
        setSaveError(describeError(caught));
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="profile-section" aria-live="polite">
        <p role="status" className="muted">Loading profile…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-section" role="alert">
        <p className="form-error">{error}</p>
        <button type="button" className="button secondary" onClick={refreshProfile}>
          Retry
        </button>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="profile-section profile-section--ruled" data-testid="profile-section">
      <div className="panel-head panel-head--row">
        <div>
          <span className="eyebrow">Organization Profile</span>
          <h4>Commercial Profile</h4>
        </div>
        <div className="profile-section__status">
          <span className="badge">{profile.verification_status}</span>
          <span className="mono profile-section__version">v{profile.version}</span>
          {!isAdmin ? (
            <span className="badge badge--warning">Read-only (Non-admin)</span>
          ) : !isEditing ? (
            <button type="button" className="button secondary" onClick={startEditing}>
              Edit profile
            </button>
          ) : null}
        </div>
      </div>

      {isStale && (
        <div className="banner banner--warning profile-section__conflict" role="alert">
          <p>
            Profile version conflict: this profile was updated by another session. Please refresh to load latest changes.
          </p>
          <button
            type="button"
            className="button"
            onClick={refreshProfile}
          >
            Refresh profile
          </button>
        </div>
      )}

      {isEditing ? (
        <form className="form" onSubmit={(e) => void handleSave(e)} noValidate>
          <div className="field">
            <label htmlFor={`capabilities-${organization.id}`}>Capabilities (comma-separated, max 50)</label>
            <input
              id={`capabilities-${organization.id}`}
              type="text"
              placeholder="e.g. Freight Forwarding, Warehousing, Port Logistics"
              value={capabilitiesDraft}
              onChange={(e) => setCapabilitiesDraft(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor={`products-${organization.id}`}>Products (comma-separated, max 50)</label>
            <input
              id={`products-${organization.id}`}
              type="text"
              placeholder="e.g. Grain, Coffee Beans, Sunflower Oil"
              value={productsDraft}
              onChange={(e) => setProductsDraft(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor={`regions-${organization.id}`}>Operating Regions (2-letter ISO country codes, comma-separated)</label>
            <input
              id={`regions-${organization.id}`}
              type="text"
              placeholder="e.g. US, CA, MX, GB"
              value={regionsDraft}
              onChange={(e) => setRegionsDraft(e.target.value)}
            />
          </div>

          <div className="profile-contacts-editor">
            <div className="profile-contacts-editor__head">
              <label>Contacts (max 20)</label>
              <button
                type="button"
                className="button ghost button--compact"
                onClick={handleAddContact}
                disabled={contactsDraft.length >= 20}
              >
                + Add contact
              </button>
            </div>
            {contactsDraft.length === 0 ? (
              <p className="muted">No contacts added yet.</p>
            ) : (
              contactsDraft.map((contact, index) => (
                <div key={index} className="profile-contact-draft">
                  <div className="profile-contact-draft__head">
                    <span className="profile-contact-draft__title">Contact #{index + 1}</span>
                    <button
                      type="button"
                      className="button ghost button--compact profile-contact-draft__remove"
                      onClick={() => handleRemoveContact(index)}
                    >
                      Remove
                    </button>
                  </div>
                  <div className="grid-2">
                    <div className="field">
                      <label htmlFor={`contact-name-${organization.id}-${index}`}>Name *</label>
                      <input
                        id={`contact-name-${organization.id}-${index}`}
                        type="text"
                        placeholder="Contact name"
                        value={contact.name}
                        onChange={(e) => handleContactChange(index, "name", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`contact-purpose-${organization.id}-${index}`}>Purpose *</label>
                      <input
                        id={`contact-purpose-${organization.id}-${index}`}
                        type="text"
                        placeholder="e.g. Commercial Disputes, Operations"
                        value={contact.purpose}
                        onChange={(e) => handleContactChange(index, "purpose", e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid-2">
                    <div className="field">
                      <label htmlFor={`contact-role-${organization.id}-${index}`}>Role Title</label>
                      <input
                        id={`contact-role-${organization.id}-${index}`}
                        type="text"
                        placeholder="e.g. Head of Trade"
                        value={contact.role_title || ""}
                        onChange={(e) => handleContactChange(index, "role_title", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`contact-vis-${organization.id}-${index}`}>Visibility</label>
                      <select
                        id={`contact-vis-${organization.id}-${index}`}
                        value={contact.visibility}
                        onChange={(e) => handleContactChange(index, "visibility", e.target.value as ContactVisibility)}
                      >
                        <option value="PRIVATE">PRIVATE (Same organization only)</option>
                        <option value="PARTICIPANTS">PARTICIPANTS (Active deal counterparties)</option>
                      </select>
                    </div>
                  </div>
                  <div className="grid-2">
                    <div className="field">
                      <label htmlFor={`contact-email-${organization.id}-${index}`}>Email</label>
                      <input
                        id={`contact-email-${organization.id}-${index}`}
                        type="email"
                        placeholder="email@example.com"
                        value={contact.email || ""}
                        onChange={(e) => handleContactChange(index, "email", e.target.value)}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`contact-phone-${organization.id}-${index}`}>Phone</label>
                      <input
                        id={`contact-phone-${organization.id}-${index}`}
                        type="tel"
                        placeholder="+1-555-0100"
                        value={contact.phone || ""}
                        onChange={(e) => handleContactChange(index, "phone", e.target.value)}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {saveError && (
            <p className="form-error" role="alert">
              {saveError}
            </p>
          )}

          <div className="actions">
            <button type="submit" className="button" disabled={saving}>
              {saving ? "Saving…" : "Save profile"}
            </button>
            <button type="button" className="button secondary" onClick={cancelEditing} disabled={saving}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="profile-dimensions">
          {/* Dimensions */}
          <div>
            <span className="profile-dimension__label">
              Capabilities
            </span>
            {profile.capabilities.length === 0 ? (
              <span className="muted">No capabilities listed</span>
            ) : (
              <div className="profile-tags">
                {profile.capabilities.map((cap) => (
                  <span key={cap} className="badge">
                    {cap}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <span className="profile-dimension__label">
              Products
            </span>
            {profile.products.length === 0 ? (
              <span className="muted">No products listed</span>
            ) : (
              <div className="profile-tags">
                {profile.products.map((prod) => (
                  <span key={prod} className="badge">
                    {prod}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <span className="profile-dimension__label">
              Operating Regions
            </span>
            {profile.regions.length === 0 ? (
              <span className="muted">No regions listed</span>
            ) : (
              <div className="profile-tags">
                {profile.regions.map((reg) => (
                  <span key={reg} className="badge">
                    {reg}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div>
            <span className="profile-dimension__label">
              Contacts
            </span>
            {profile.contacts.length === 0 ? (
              <p className="muted">No contacts listed.</p>
            ) : (
              <ul className="profile-contacts">
                {profile.contacts.map((contact) => (
                  <li key={contact.id || contact.name} className="profile-contact">
                    <div className="profile-contact__body">
                      <div className="profile-contact__identity">
                        <strong>{contact.name}</strong>
                        {contact.role_title && <span className="muted">— {contact.role_title}</span>}
                      </div>
                      <div className="muted profile-contact__detail">
                        <span>Purpose: {contact.purpose}</span>
                        {contact.email && <span> · Email: {contact.email}</span>}
                        {contact.phone && <span> · Phone: {contact.phone}</span>}
                      </div>
                    </div>
                    <div>
                      {contact.visibility === "PRIVATE" ? (
                        <span className="badge badge--private" data-testid="contact-visibility-badge">
                          Private
                        </span>
                      ) : (
                        <span className="badge badge--shareable" data-testid="contact-visibility-badge">
                          Participants
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
