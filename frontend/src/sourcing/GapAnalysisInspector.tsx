import React from "react";
import type { CommercialGap } from "./sourcingTypes";

export interface GapAnalysisInspectorProps {
  gaps: CommercialGap[];
  inspectedGap: CommercialGap | null;
  onInspectGap: (gap: CommercialGap | null) => void;
}

export const GapAnalysisInspector: React.FC<GapAnalysisInspectorProps> = ({
  gaps,
  inspectedGap,
  onInspectGap,
}) => {
  return (
    <div className="gap-analysis-drawer" data-testid="gap-analysis-drawer">
      <h3>Detected Commercial Gaps ({gaps.length})</h3>
      {gaps.length === 0 ? (
        <p className="no-gaps-text">
          No commercial gaps detected. Listing is 100% compliant and ready for deal initiation.
        </p>
      ) : (
        <ul className="gaps-list">
          {gaps.map((gap) => (
            <li
              key={gap.gap_id}
              className={`gap-item severity-${gap.severity.toLowerCase()}`}
              onClick={() => onInspectGap(gap)}
            >
              <div className="gap-item-header">
                <span className="gap-field">{gap.field_name}</span>
                <span className="badge category-badge">{gap.category}</span>
                <span className={`badge severity-badge severity-${gap.severity.toLowerCase()}`}>
                  {gap.severity}
                </span>
              </div>
              <p className="gap-explanation">{gap.explanation}</p>
              <p className="gap-action">
                <strong>Action:</strong> {gap.suggested_action}
              </p>
            </li>
          ))}
        </ul>
      )}
      {inspectedGap && (
        <div className="inspected-gap-detail" data-testid="inspected-gap-detail">
          Inspected: {inspectedGap.field_name} ({inspectedGap.category})
        </div>
      )}
    </div>
  );
};
