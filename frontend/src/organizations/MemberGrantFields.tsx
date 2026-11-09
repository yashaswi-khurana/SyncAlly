import { useEffect, useState } from "react";
import { listAssignableOrganizationDeals } from "../api/client";
import type { AssignableDeal } from "../api/types";

export interface MemberGrants {
  role_bundles: string[];
  permissions: string[];
  deal_ids: string[];
}

const BUNDLES = ["DEAL_MANAGER", "DEAL_MEMBER", "APPROVER", "FINANCE", "FULFILLMENT"];
const PERMISSIONS = ["deal.create", "deal.edit_assigned", "agreement.approve", "payments.read", "payments.authorize", "fulfillment.read", "fulfillment.record", "marketplace.manage", "approval_routing.manage"];
const BUNDLE_PERMISSIONS: Record<string, string[]> = {
  DEAL_MANAGER: ["deal.create", "deal.assign", "deal.read_assigned", "deal.edit_assigned"],
  DEAL_MEMBER: ["deal.read_assigned", "deal.edit_assigned"],
  APPROVER: ["deal.read_assigned", "agreement.approve"],
  FINANCE: ["deal.read_assigned", "payments.read", "payments.authorize"],
  FULFILLMENT: ["deal.read_assigned", "fulfillment.read", "fulfillment.record"],
};

export default function MemberGrantFields({
  organizationId,
  isOwner = false,
  disabled = false,
  initialDealId,
  onChange,
}: {
  organizationId: string;
  isOwner?: boolean;
  disabled?: boolean;
  initialDealId?: string;
  onChange: (grants: MemberGrants) => void;
}) {
  const [deals, setDeals] = useState<AssignableDeal[]>([]);
  const [bundles, setBundles] = useState<string[]>([]);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [dealIds, setDealIds] = useState<string[]>(initialDealId ? [initialDealId] : []);
  const bundledPermissions = new Set(bundles.flatMap((bundle) => BUNDLE_PERMISSIONS[bundle] || []));
  const toggle = (list: string[], setList: (value: string[]) => void, key: string) =>
    setList(list.includes(key) ? list.filter((value) => value !== key) : [...list, key]);

  useEffect(() => {
    let cancelled = false;
    void listAssignableOrganizationDeals(organizationId).then((result) => {
      if (!cancelled) setDeals(result);
    }).catch(() => { if (!cancelled) setDeals([]); });
    return () => { cancelled = true; };
  }, [organizationId]);

  useEffect(() => onChange({ role_bundles: bundles, permissions, deal_ids: dealIds }), [bundles, permissions, dealIds, onChange]);

  return <>
    <fieldset className="field control-rows">
      <legend>Permission bundles</legend>
      <p className="muted">Select the actions this member needs. Bundles can be combined.</p>
      {BUNDLES.map((bundle) => <label key={bundle}>
        <input type="checkbox" disabled={disabled} checked={bundles.includes(bundle)} onChange={() => toggle(bundles, setBundles, bundle)} /> {bundle.replaceAll("_", " ")}
      </label>)}
      {isOwner ? <label><input type="checkbox" disabled={disabled} checked={bundles.includes("ORG_ADMIN")} onChange={() => {
        if (!bundles.includes("ORG_ADMIN") && !window.confirm("Grant organization administration, including profile and member management?")) return;
        toggle(bundles, setBundles, "ORG_ADMIN");
      }} /> Organization administrator</label> : null}
    </fieldset>
    <fieldset className="field control-rows">
      <legend>Additional permissions</legend>
      {isOwner ? <label><input type="checkbox" disabled={disabled} checked={permissions.includes("deal.read_all")} onChange={() => {
        if (!permissions.includes("deal.read_all") && !window.confirm("Grant access to every current and future deal in this organization?")) return;
        toggle(permissions, setPermissions, "deal.read_all");
      }} /> Read all organization deals</label> : null}
      {PERMISSIONS.map((permission) => <label key={permission}>
        <input type="checkbox" disabled={disabled || bundledPermissions.has(permission)} checked={permissions.includes(permission) || bundledPermissions.has(permission)} onChange={() => toggle(permissions, setPermissions, permission)} /> {permission}{bundledPermissions.has(permission) ? " (included in selected bundle)" : ""}
      </label>)}
    </fieldset>
    <fieldset className="field control-rows">
      <legend>Deal access</legend>
      {deals.length === 0 ? <p className="muted">No deals available to assign.</p> : deals.map((deal) => <label key={deal.id}>
        <input type="checkbox" disabled={disabled} checked={dealIds.includes(deal.id)} onChange={() => toggle(dealIds, setDealIds, deal.id)} /> {deal.display_name} ({deal.status})
      </label>)}
      <p className="muted">No deals are selected by default. Deal access does not grant approval, payment, or editing actions.</p>
    </fieldset>
  </>;
}
