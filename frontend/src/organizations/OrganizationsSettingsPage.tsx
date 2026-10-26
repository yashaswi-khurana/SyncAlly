import OrganizationsPanel from "./OrganizationsPanel";
import Reveal from "../ui/Reveal";

export default function OrganizationsSettingsPage() {
  return (
    <div className="workspace">
      <Reveal className="hero">
        <div className="workspace-intro__meta">
          <span className="eyebrow">Settings / Organizations</span>
          <span className="workspace-intro__caption">Counterparty directory &amp; members</span>
        </div>
        <h1 className="display">Organizations.</h1>
        <p className="hero__lede">
          Share your organization IDs with counterparties to create deals, manage registered trading
          entities, and invite team members.
        </p>
      </Reveal>

      <Reveal delay={80}>
        <OrganizationsPanel />
      </Reveal>
    </div>
  );
}

