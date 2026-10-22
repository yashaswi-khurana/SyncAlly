"""HTTP endpoint for safe, committed-agreement document drafts."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from syncally.api.auth import get_current_actor
from syncally.api.deals import get_deal_repository
from syncally.application.agreements import AgreementNotFound
from syncally.application.deals import DealNotFound, DealRepository
from syncally.application.documents import (
    AgreementNotCommitted,
    CommercialDocumentDraft,
    generate_commercial_document_draft,
)
from syncally.application.identity import ActorContext
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
