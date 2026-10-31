import { useLayoutEffect, useRef, useState } from "react";

import { ApiError, getTradePack } from "../api/client";
import type { TradePackFormat } from "../api/client";
import type { AgreementVersion } from "../api/types";
import { getAccessToken } from "../api/tokenStore";

interface CommercialDocumentPanelProps {
  dealId: string;
  agreement: AgreementVersion;
  organizationId: string;
  contextKey: string;
}

export default function CommercialDocumentPanel({ dealId, agreement, organizationId, contextKey }: CommercialDocumentPanelProps) {
  const [format, setFormat] = useState<TradePackFormat>("zip");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const request = useRef<AbortController | null>(null);
  const objectUrls = useRef(new Set<string>());
  const identity = JSON.stringify([contextKey, dealId, organizationId, agreement.id,
    agreement.version_number, agreement.terms_hash, agreement.status]);
  const [observedIdentity, setObservedIdentity] = useState(identity);
  if (identity !== observedIdentity) {
    setObservedIdentity(identity);
    setPending(false);
    setError("");
  }
  useLayoutEffect(() => {
    const urls = objectUrls.current;
    return () => {
      request.current?.abort();
      for (const url of urls) URL.revokeObjectURL(url);
      urls.clear();
    };
  }, [identity]);

  async function download() {
    if (request.current && !request.current.signal.aborted) return;
    const controller = new AbortController();
    request.current = controller;
    const token = getAccessToken();
    setPending(true);
    setError("");
    try {
      const blob = await getTradePack(dealId, agreement, organizationId, format, controller.signal);
      if (controller.signal.aborted || token !== getAccessToken()) return;
      const filename = `syncally-deal-${dealId}-agreement-v${agreement.version_number}-trade-pack.${format}`;
      if (!/^[A-Za-z0-9.-]+$/.test(filename)) throw new Error("Invalid document filename");
      const url = URL.createObjectURL(blob);
      objectUrls.current.add(url);
      const link = document.createElement("a");
      try {
        link.href = url;
        link.download = filename;
        document.body.append(link);
        link.click();
      } finally {
        link.remove();
        window.setTimeout(() => {
          if (objectUrls.current.delete(url)) URL.revokeObjectURL(url);
        }, 0);
      }
    } catch (caught) {
      if (!controller.signal.aborted && token === getAccessToken()) {
        setError(caught instanceof ApiError ? caught.message : "Unable to download the trade pack. Please try again.");
      }
    } finally {
      if (request.current === controller) {
        request.current = null;
        if (!controller.signal.aborted) setPending(false);
      }
    }
  }

  return (
    <section className="document-status" aria-labelledby="document-status-heading">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Committed source</span>
          <h3 id="document-status-heading">Trade pack</h3>
        </div>
      </div>
      <p>Version {agreement.version_number} · DRAFT - FOR REVIEW ONLY</p>
      <label htmlFor="trade-pack-format">Document format</label>
      <select id="trade-pack-format" value={format} disabled={pending}
        onChange={(event) => setFormat(event.target.value as TradePackFormat)}>
        <option value="zip">ZIP</option><option value="html">HTML</option>
      </select>
      <button type="button" className="button secondary" disabled={pending || agreement.status !== "COMMITTED" || !agreement.id || !organizationId}
        onClick={() => void download()}>{pending ? "Downloading…" : "Download trade pack"}</button>
      {error ? <p role="alert">{error}</p> : null}
    </section>
  );
}
