import TradeFlowScene from "./TradeFlowScene";

interface DealConstellationProps {
  buyerOrganizationId: string;
  sellerOrganizationId: string;
}

export default function DealConstellation({
  buyerOrganizationId,
  sellerOrganizationId,
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
      <span className="deal-constellation__id deal-constellation__id--buyer">
        {buyerOrganizationId.slice(0, 8)}
      </span>
      <span className="deal-constellation__id deal-constellation__id--seller">
        {sellerOrganizationId.slice(0, 8)}
      </span>
    </div>
  );
}
