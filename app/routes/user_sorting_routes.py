from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import func

from app.database import get_db
from app.models.project import Project
from app.models.user_sorting_mapping import UserSortingMapping
from app.schemas.user_sorting_schema import UserProjectReorderRequest
from app.schemas.project_schema import ProjectOut
from app.helpers.auth import get_current_user
from app.schemas.authschema import CurrentUser


router = APIRouter(tags=["user-sorting"])

@router.get("/users/{user_id}/projects", response_model=list[ProjectOut])
def list_projects_for_user(user_id: int, db: Session = Depends(get_db)):
    usm = aliased(UserSortingMapping)

    rows = (
        db.query(
            Project,
            func.coalesce(usm.sort_order, Project.sort_order).label("effective_order"),
        )
        .outerjoin(
            usm,
            (usm.project_id == Project.id) & (usm.user_id == user_id),
        )
        .filter(Project.is_active == True)
        .order_by("effective_order")
        .all()
    )

    projects = [p for p, _ in rows]
    return [ProjectOut.from_orm(p) for p in projects]



@router.put(
    "/users/{user_id}/projects/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
)
def reorder_user_projects(
    user_id: int,
    payload: UserProjectReorderRequest,
    db: Session = Depends(get_db),
):
    if user_id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User id mismatch in payload",
        )

    items = payload.items
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reorder payload",
        )

    proj_ids = [i.project_id for i in items]

    projects = (
        db.query(Project)
        .filter(Project.id.in_(proj_ids), Project.is_active == True)
        .all()
    )
    valid_ids = {p.id for p in projects}
    for pid in proj_ids:
        if pid not in valid_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid project id in reorder payload",
            )

    mappings = (
        db.query(UserSortingMapping)
        .filter(
            UserSortingMapping.user_id == user_id,
            UserSortingMapping.project_id.in_(proj_ids),
        )
        .all()
    )
    by_pid = {m.project_id: m for m in mappings}

    for item in items:
        row = by_pid.get(item.project_id)
        if not row:
            row = UserSortingMapping(
                user_id=user_id,
                project_id=item.project_id,
            )
            db.add(row)
        row.sort_order = item.position

    db.commit()
    return None

