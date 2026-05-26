from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.memberships import Membership
from app.db.models.users import User
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.memberships.repository import MembershipRepository

membership_repository = MembershipRepository()



def get_current_membership(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    company_id: str | None = Header(default=None, alias="X-Company-Id"),
) -> Membership:
    memberships = membership_repository.list_by_user_id(db, str(current_user.id))
    if not memberships:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario sem empresa vinculada.",
        )

    if company_id:
        membership = membership_repository.get_by_user_and_company(db, str(current_user.id), company_id)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sem acesso a empresa informada.",
            )
        return membership

    if len(memberships) == 1:
        return memberships[0]

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Informe o header X-Company-Id para selecionar a empresa ativa.",
    )