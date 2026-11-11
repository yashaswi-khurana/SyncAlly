import TradeFlowScene from "./TradeFlowScene";

interface DealConstellationProps {
  buyerOrganizationId: string;
  sellerOrganizationId: string;
  buyerName?: string;
  sellerName?: string;
}

export default function DealConstellation({
  buyerOrganizationId,
  sellerOrganizationId,
  buyerName,
  sellerName,
}: DealConstellationProps) {
  return (
    <div className="deal-constellation" aria-hidden="true">
      <div className="deal-constellation__diagram">
        <TradeFlowScene />
      </div>
      <div className="deal-constellation__labels">
        <span>Buyer</span>
        <span>Shared record</span>
        <span>Seller</span>
      </div>
      <span className="deal-constellation__id deal-constellation__id--buyer" title={buyerOrganizationId}>
        {buyerName || buyerOrganizationId.slice(0, 8)}
      </span>
      <span className="deal-constellation__id deal-constellation__id--seller" title={sellerOrganizationId}>
        {sellerName || sellerOrganizationId.slice(0, 8)}
      </span>
    </div>
  );
}
