"""Users routes (contracts/users.md)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from repse.auth.dependencies import CurrentUser, current_user, require_role
from repse.auth.passwords import hash_password
from repse.db.session import get_db
from repse.errors import Conflict, NotFound
from repse.users.models import Role, User, UserStatus
from repse.users.schemas import UserCreate, UserOut, UserPatch

router = APIRouter()


@router.get("")
def list_users(
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    rows = db.execute(select(User).order_by(User.email)).scalars().all()
    return {
        "items": [UserOut.model_validate(u).model_dump() for u in rows],
        "next_cursor": None,
        "has_more": False,
    }


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate,
    user: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> User:
    existing = db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none()
    if existing is not None:
        raise Conflict("Email already exists in this organization", details={"code": "email_exists"})
    new = User(
        organization_id=user.organization_id,
        email=body.email.lower(),
        display_name=body.display_name,
        role=body.role,
        status=UserStatus.ACTIVE,
        password_hash=hash_password(body.password) if body.password else None,
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserPatch,
    actor: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> User:
    row = db.get(User, user_id)
    if row is None:
        raise NotFound("User not found")
    if body.display_name is not None:
        row.display_name = body.display_name
    if body.role is not None:
        # Disallow demoting the last admin.
        if row.role is Role.ADMIN and body.role is not Role.ADMIN:
            _guard_last_admin(db, actor.organization_id, exclude_user_id=row.id)
        row.role = body.role
    if body.status is not None:
        if body.status is UserStatus.DISABLED and row.role is Role.ADMIN:
            _guard_last_admin(db, actor.organization_id, exclude_user_id=row.id)
        row.status = body.status
    if body.password is not None:
        row.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{user_id}", status_code=204)
def deactivate_user(
    user_id: int,
    actor: CurrentUser = Depends(require_role(Role.ADMIN.value)),
    db: Session = Depends(get_db),
) -> Response:
    row = db.get(User, user_id)
    if row is None:
        raise NotFound("User not found")
    if row.role is Role.ADMIN:
        _guard_last_admin(db, actor.organization_id, exclude_user_id=row.id)
    row.status = UserStatus.DISABLED
    db.commit()
    return Response(status_code=204)


def _guard_last_admin(db: Session, organization_id: int, *, exclude_user_id: int) -> None:
    count = db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.role == Role.ADMIN,
            User.status == UserStatus.ACTIVE,
            User.id != exclude_user_id,
        )
    ).scalar_one()
    if count < 1:
        raise Conflict(
            "Cannot leave the organization without active admins",
            details={"code": "last_admin"},
        )
