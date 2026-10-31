"""HTTP endpoint for safe, committed-agreement document drafts."""

import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.deals import get_deal_repository
from syncally.application.agreements import (
    AgreementNotFound,
)
from syncally.application.deals import DealNotFound, DealRepository
from syncally.application.documents import (
    AgreementNotCommitted,
    CommercialDocumentDraft,
    TradePackTooLarge,
    generate_commercial_document_draft,
    generate_trade_pack,
)
from syncally.application.identity import ActorContext
from syncally.domain.shared.errors import DomainError
from syncally.infrastructure.database import get_db
from syncally.infrastructure.repositories.agreements import SqlAlchemyAgreementRepository

router = APIRouter(prefix="/deals/{deal_id}/documents", tags=["documents"])


class CommercialDocumentDraftResponse(BaseModel):
    """Rendered trade summary and the committed agreement version it came from."""

    agreement_version_id: UUID
    agreement_version_number: int
    terms_hash: str
    content: str


@router.get("/commercial-draft", response_model=CommercialDocumentDraftResponse)
def get_commercial_document_draft_route(
    deal_id: UUID,
    actor: ActorContext = Depends(get_current_actor),
    deal_repository: DealRepository = Depends(get_deal_repository),
    db: Session = Depends(get_db),
) -> CommercialDocumentDraftResponse:
    """Generate a read-only document from the deal's committed agreement."""
    try:
        draft: CommercialDocumentDraft = generate_commercial_document_draft(
            actor,
            deal_id,
            deal_repository,
            SqlAlchemyAgreementRepository(db),
        )
    except DealNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deal not found") from error
    except AgreementNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A committed agreement is required before this document is available.",
        ) from error
    except AgreementNotCommitted as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A committed agreement is required before this document is available.",
        ) from error

    return CommercialDocumentDraftResponse(
        agreement_version_id=draft.agreement_version_id,
        agreement_version_number=draft.agreement_version_number,
        terms_hash=draft.terms_hash,
        content=draft.content,
    )


@router.get("/versions/{number}/trade-pack")
def get_trade_pack_route(
    deal_id: UUID, agreement_version_id: UUID, organization_id: UUID,
    number: int = Path(ge=1), terms_hash: str = Query(pattern=r"^[0-9a-f]{64}$"),
    format: Literal["zip", "html"] = "zip",
    actor: ActorContext = Depends(get_current_actor), db: Session = Depends(get_db),
) -> Response:
    try:
        result = SqlAlchemyAgreementRepository(db).read_versions(
            deal_id, actor.user_id, organization_id, (number,), commitment_only=True,
        )
        pack = generate_trade_pack(result["versions"][0], deal_id=deal_id, number=number,
            agreement_version_id=agreement_version_id, terms_hash=terms_hash, format=format)
    except AgreementNotFound as error:
        raise HTTPException(404, "Deal or agreement version not found") from error
    except TradePackTooLarge as error:
        raise HTTPException(413, str(error)) from error
    except (DomainError,
            ValueError, TypeError, KeyError, ArithmeticError) as error:
        raise HTTPException(409, "A consistent, bilaterally approved committed version is required") from error
    if not pack.filename.isascii() or not re.fullmatch(r"[A-Za-z0-9.-]+", pack.filename):
        raise HTTPException(409, "Invalid document filename")
    return Response(pack.content, media_type=pack.media_type, headers={
        "Content-Disposition": f'attachment; filename="{pack.filename}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'",
    })
