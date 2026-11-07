import { useCallback, useEffect, useState } from "react";

import { ApiError, listPlatformOrganizations, updatePlatformOrganizationStatus } from "../api/client";
import type { PlatformOrganization } from "../api/types";

export default function PlatformOrganizationsPage() {
  const [organizations, setOrganizations] = useState<PlatformOrganization[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      setOrganizations(await listPlatformOrganizations());
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 403
        ? "This account does not have platform administrator access."
        : "Could not load organizations. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function changeStatus(organization: PlatformOrganization) {
    const nextStatus = organization.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
    if (nextStatus === "SUSPENDED" && !window.confirm(
      `Suspend ${organization.legal_name}? Its members will lose access to this organization until it is reactivated.`,
    )) return;
    setBusyId(organization.id);
    setError(null);
    try {
      const updated = await updatePlatformOrganizationStatus(organization.id, nextStatus);
      setOrganizations((current) => current.map((item) => item.id === updated.id ? updated : item));
    } catch {
      setError("The organization status could not be changed. Refresh and try again.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="card" aria-labelledby="platform-organizations-heading">
      <div className="page-header">
        <div>
          <p className="eyebrow">PLATFORM ADMINISTRATION</p>
          <h1 id="platform-organizations-heading">Organizations</h1>
          <p>Manage organization access. Private deals, agreements, and payment records remain organization-scoped.</p>
        </div>
        <button type="button" className="button secondary" onClick={() => void refresh()} disabled={loading}>
          Refresh
        </button>
      </div>

      {error ? <p role="alert" className="form-error">{error}</p> : null}
      {loading ? <p role="status">Loading organizations…</p> : null}
      {!loading && !error && organizations.length === 0 ? <p>No organizations have been created yet.</p> : null}
      {!loading && organizations.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
            <thead>
              <tr><th scope="col">Organization</th><th scope="col">Country</th><th scope="col">Status</th><th scope="col">Created</th><th scope="col">Action</th></tr>
            </thead>
            <tbody>
              {organizations.map((organization) => (
                <tr key={organization.id}>
                  <th scope="row">{organization.legal_name}</th>
                  <td>{organization.country_code}</td>
                  <td>{organization.status}</td>
                  <td>{organization.created_at ? new Date(organization.created_at).toLocaleDateString() : "—"}</td>
                  <td>
                    {organization.status === "ACTIVE" || organization.status === "SUSPENDED" ? (
                      <button
                        type="button"
                        className="button ghost"
                        disabled={busyId === organization.id}
                        onClick={() => void changeStatus(organization)}
                      >
                        {busyId === organization.id
                          ? "Saving…"
                          : organization.status === "ACTIVE" ? "Suspend" : "Reactivate"}
                      </button>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
