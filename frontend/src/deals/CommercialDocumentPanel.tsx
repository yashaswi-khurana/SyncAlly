import { useEffect, useState } from "react";

import { ApiError, getCommercialDocumentDraft } from "../api/client";
import type { CommercialDocumentDraft } from "../api/types";

type DocumentState =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "error"; message: string }
  | { status: "ready"; draft: CommercialDocumentDraft };

interface CommercialDocumentPanelProps {
  dealId: string;
}

export default function CommercialDocumentPanel({ dealId }: CommercialDocumentPanelProps) {
  const [state, setState] = useState<DocumentState>({ status: "loading" });
  const [reloadCount, setReloadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    void getCommercialDocumentDraft(dealId).then(
      (draft) => {
        if (!cancelled) setState({ status: "ready", draft });
      },
      (caught: unknown) => {
        if (cancelled) return;
        if (caught instanceof ApiError && caught.status === 409) {
          setState({ status: "unavailable" });
          return;
        }
        setState({
          status: "error",
          message:
            caught instanceof ApiError
              ? caught.message
              : "Unable to load the trade summary. Please try again.",
        });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [dealId, reloadCount]);

  function retry() {
    setState({ status: "loading" });
    setReloadCount((count) => count + 1);
  }

  function downloadDraft(draft: CommercialDocumentDraft) {
    const url = URL.createObjectURL(
      new Blob([draft.content], { type: "text/plain;charset=utf-8" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `syncally-deal-${dealId}-agreement-v${draft.agreement_version_number}-draft.txt`;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  return (
    <section className="card document-status" aria-labelledby="document-status-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Committed source</span>
          <h2 id="document-status-heading">Trade summary</h2>
        </div>
        <button type="button" className="button secondary button--compact" onClick={retry}>
          Refresh document
        </button>
      </div>

      {state.status === "loading" ? <p role="status">Checking document availability…</p> : null}
      {state.status === "unavailable" ? (
        <p className="payment-status__message" role="status">
          This review-only draft is available after both parties commit the same agreement version.
        </p>
      ) : null}
      {state.status === "error" ? (
        <p className="payment-status__message" role="alert">
          The trade summary is unavailable. {state.message}
        </p>
      ) : null}
      {state.status === "ready" ? (
        <div className="document-status__ready">
          <p>
            Draft from committed agreement version {state.draft.agreement_version_number}. It does
            not change the agreement.
          </p>
          <button
            type="button"
            className="button secondary"
            onClick={() => downloadDraft(state.draft)}
          >
            Download trade summary
          </button>
        </div>
      ) : null}
    </section>
  );
}
