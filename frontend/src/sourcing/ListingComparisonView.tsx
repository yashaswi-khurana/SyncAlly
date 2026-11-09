import React from "react";
import type { CandidateComparisonResult } from "./sourcingTypes";

export interface ListingComparisonViewProps {
  candidates: CandidateComparisonResult[];
  selectedCandidate: CandidateComparisonResult | null;
  onSelectCandidate: (candidate: CandidateComparisonResult) => void;
  onOpenInquiry: (candidate: CandidateComparisonResult) => void;
  selectedSector: string;
  onSectorChange: (sector: string) => void;
  children?: React.ReactNode;
}

export const ListingComparisonView: React.FC<ListingComparisonViewProps> = ({
  candidates,
  selectedCandidate,
  onSelectCandidate,
  onOpenInquiry,
  selectedSector,
  onSectorChange,
  children,
}) => {
  const filteredCandidates = selectedSector === "All"
    ? candidates
    : candidates.filter((c) =>
        c.category.toLowerCase().includes(selectedSector.toLowerCase()) ||
        (selectedSector.toLowerCase().startsWith("agri") && c.category.toLowerCase().includes("agri"))
      );

  return (
    <div className="sourcing-comparison-view">
      {/* Sector Filter */}
      <div className="sector-filter-controls">
        <label htmlFor="sector-filter">Filter by Sector:</label>
        <select
          id="sector-filter"
          value={selectedSector}
          onChange={(e) => onSectorChange(e.target.value)}
        >
          <option value="All">All Sectors</option>
          <option value="Fasteners">Industrial Fasteners</option>
          <option value="Electronics">Electronics</option>
          <option value="Agriculture">Agricultural Commodities</option>
          <option value="Textiles">Textiles</option>
          <option value="Medical">Medical Supplies</option>
        </select>
      </div>

      {/* Candidate Listings Cards */}
      <section className="candidate-listings-section" aria-label="Candidate Listings">
        <h2>Candidate Listings ({filteredCandidates.length})</h2>
        <div className="candidate-cards-grid">
          {filteredCandidates.map((candidate) => (
            <div
              key={candidate.listing_id}
              className={`candidate-card ${selectedCandidate?.listing_id === candidate.listing_id ? "selected" : ""}`}
              onClick={() => onSelectCandidate(candidate)}
              data-testid={`listing-card-${candidate.listing_id}`}
            >
              <div className="card-header">
                <h3>{candidate.listing_title}</h3>
                <span className={`badge tier-${candidate.match_tier.toLowerCase()}`}>
                  Tier {candidate.match_tier} ({candidate.composite_score.toFixed(0)}%)
                </span>
              </div>
              <p className="org-name">{candidate.seller_organization_name} ({candidate.country_code})</p>
              <div className="card-metrics">
                <span>Price: ${candidate.unit_price} {candidate.currency}</span>
                <span>MOQ: {candidate.moq}</span>
                <span>Lead: {candidate.lead_time_days ? `${candidate.lead_time_days}d` : "Missing"}</span>
              </div>
              <div className="card-actions">
                <button
                  type="button"
                  className="inquiry-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenInquiry(candidate);
                  }}
                >
                  Draft Inquiry
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Selected Candidate Detailed Matrix */}
      {selectedCandidate && (
        <section className="detailed-evaluation-section" aria-label="Detailed Evaluation">
          <h2>Attribute Comparison Matrix — {selectedCandidate.seller_organization_name}</h2>
          <table className="comparison-matrix-table" data-testid="comparison-matrix-table">
            <thead>
              <tr>
                <th>Attribute</th>
                <th>Buyer Requirement</th>
                <th>Candidate Offering</th>
                <th>Variance / Delta</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {selectedCandidate.attribute_matrix.map((row, idx) => (
                <tr key={idx} className={`status-${row.status.toLowerCase()}`}>
                  <td><strong>{row.attribute}</strong></td>
                  <td>{row.buyer_requirement}</td>
                  <td>{row.candidate_value}</td>
                  <td>{row.variance}</td>
                  <td>
                    <span className={`status-badge status-${row.status.toLowerCase()}`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {children}
        </section>
      )}
    </div>
  );
};
