from fastapi import Depends, HTTPException, status

from app.db.models.memberships import Membership
from app.modules.memberships.dependencies import get_current_membership


ALLOWED_ADMIN_ROLES = {"OWNER", "ADMIN"}
ALLOWED_MANAGER_ROLES = {"OWNER", "ADMIN", "MANAGER"}
ALLOWED_OPERATOR_ROLES = {"OWNER", "ADMIN", "MANAGER", "INSPECTOR"}


def require_membership_roles(*roles: str):
    allowed_roles = set(roles)

    def dependency(membership: Membership = Depends(get_current_membership)) -> Membership:
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario sem permissao para executar esta acao.",
            )
        return membership

    return dependency


def get_admin_membership(
    membership: Membership = Depends(require_membership_roles(*ALLOWED_ADMIN_ROLES)),
) -> Membership:
    return membership


def get_manager_membership(
    membership: Membership = Depends(require_membership_roles(*ALLOWED_MANAGER_ROLES)),
) -> Membership:
    return membership


def get_operator_membership(
    membership: Membership = Depends(require_membership_roles(*ALLOWED_OPERATOR_ROLES)),
) -> Membership:
    return membership
