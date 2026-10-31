export function invitationPresentation(token: string | null): {
  kind: "LEGACY" | "TEAM" | "COUNTERPARTY" | "INVALID";
  recipientEmail?: string;
} {
  if (!token) return { kind: "LEGACY" };
  try {
    const encoded = token.split(".")[1].replaceAll("-", "+").replaceAll("_", "/");
    const bytes = Uint8Array.from(atob(encoded), (character) => character.charCodeAt(0));
    const claims: unknown = JSON.parse(new TextDecoder().decode(bytes));
    if (!claims || typeof claims !== "object") return { kind: "INVALID" };
    const values = claims as Record<string, unknown>;
    if (!["version", "kind", "recipient_email", "buyer_id", "shell_id"].some((key) => key in values)) {
      return { kind: "LEGACY" };
    }
    if (values.version !== 1 || (values.kind !== "TEAM" && values.kind !== "COUNTERPARTY") || typeof values.recipient_email !== "string") {
      return { kind: "INVALID" };
    }
    return { kind: values.kind, recipientEmail: values.recipient_email };
  } catch {
    return { kind: "LEGACY" };
  }
}