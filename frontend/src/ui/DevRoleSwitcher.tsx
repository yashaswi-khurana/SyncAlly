import { useEffect, useState } from "react";

import { apiRequest, listOrganizations } from "../api/client";
import { getAccessToken, setTokens } from "../api/tokenStore";
import type { TokenResponse } from "../api/types";

const SWITCHER_ENABLED =
  import.meta.env.DEV ||
  (import.meta.env as ImportMetaEnv & { VITE_ENABLE_DEV_SWITCHER?: string })
    .VITE_ENABLE_DEV_SWITCHER === "true";

type DemoRole = "Buyer" | "Seller" | "Admin";

interface DevRoleSwitcherProps {
  onSessionChanged: () => void;
}

export default function DevRoleSwitcher({ onSessionChanged }: DevRoleSwitcherProps) {
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<DemoRole>("Admin");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState("");

  useEffect(() => {
    if (!SWITCHER_ENABLED) return;

    let disposed = false;

    async function syncRoleFromSession() {
      const sessionToken = getAccessToken();
      if (!sessionToken) {
        setRole("Admin");
        return;
      }

      try {
        const organizations = await listOrganizations();
        if (disposed || getAccessToken() !== sessionToken) return;
        if (organizations.some((organization) => organization.legal_name === "Demo Seller Co")) {
          setRole("Seller");
        } else if (
          organizations.some((organization) => organization.legal_name === "Demo Buyer Co")
        ) {
          setRole("Buyer");
        } else {
          setRole("Admin");
        }
      } catch {
        // Keep the neutral label if the authenticated identity cannot be loaded.
      }
    }

    const handleStorage = (event: StorageEvent) => {
      if (event.key === null || event.key === "syncally.accessToken") {
        void syncRoleFromSession();
      }
    };

    void syncRoleFromSession();
    window.addEventListener("storage", handleStorage);
    return () => {
      disposed = true;
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  if (!SWITCHER_ENABLED) return null;

  async function switchRole(targetRole: DemoRole) {
    const sessionToken = getAccessToken();
    if (!sessionToken) return;
    setBusy(true);
    setFeedback("");
    try {
      const tokens = await apiRequest<TokenResponse>("/dev/switch-role", {
        method: "POST",
        body: JSON.stringify({ target_role: targetRole.toUpperCase() }),
      });
      if (getAccessToken() !== sessionToken) return;
      setTokens(tokens);
      setRole(targetRole);
      onSessionChanged();
      setFeedback(`Switched to ${targetRole}.`);
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Could not switch role.");
    } finally {
      setBusy(false);
    }
  }

  async function resetDemo() {
    if (!window.confirm("Reset demo data? This clears demo deals and related activity.")) return;
    setBusy(true);
    setFeedback("");
    try {
      await apiRequest<{ message: string }>("/dev/reset-demo", { method: "POST" });
      onSessionChanged();
      setFeedback("Demo data reset.");
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : "Could not reset demo data.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="dev-role-switcher" aria-label="Development role switcher">
      {feedback && <div className="dev-role-switcher__toast" role="status">{feedback}</div>}
      {open && (
        <div className="dev-role-switcher__menu" role="group" aria-label="Development actions">
          <button type="button" disabled={busy} onClick={() => void switchRole("Buyer")}>
            Switch to Buyer
          </button>
          <button type="button" disabled={busy} onClick={() => void switchRole("Seller")}>
            Switch to Seller
          </button>
          <button type="button" disabled={busy} onClick={() => void resetDemo()}>
            Reset Demo Data
          </button>
        </div>
      )}
      <button
        type="button"
        className="dev-role-switcher__pill"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="dev-role-switcher__indicator" aria-hidden="true" />
        Acting as {role}
      </button>
    </aside>
  );
}
