from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.enums import ApplicationStatus, NotificationType, ProjectStatus
from app.models import Application, Project, ProjectMember, ProjectRole
from app.schemas.application import ApplicationCreate, ApplicationOut, ApplicationStatusUpdate
from app.services.notifications import notify

router = APIRouter(tags=["applications"])


def _get_application(db, app_id: int) -> Application:
    application = db.get(Application, app_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    return application


@router.post(
    "/projects/{project_id}/apply",
    response_model=ApplicationOut,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_project(project_id: int, payload: ApplicationCreate, user: CurrentUser, db: DbSession):
    """Submit the formal join request (availability, timezone, abilities, pitch, reward)."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.status != ProjectStatus.OPEN:
        raise HTTPException(status.HTTP_409_CONFLICT, "This project is closed to applications")
    if project.owner_id == user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot apply to your own project")
    if db.scalar(
        select(Application.id).where(
            Application.project_id == project_id, Application.applicant_id == user.id
        )
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "You have already applied to this project")
    if payload.role_id is not None:
        role = db.get(ProjectRole, payload.role_id)
        if role is None or role.project_id != project_id:
            raise HTTPException(422, "role_id does not belong to this project")

    application = Application(project_id=project_id, applicant_id=user.id, **payload.model_dump())
    db.add(application)
    db.flush()
    notify(
        db,
        project.owner_id,
        NotificationType.APPLICATION_RECEIVED,
        application_id=application.id,
        project_id=project.id,
        project_title=project.title,
        applicant_id=user.id,
        applicant_username=user.username,
    )
    db.commit()
    return application


@router.get("/projects/{project_id}/applications", response_model=list[ApplicationOut])
def list_project_applications(
    project_id: int, user: CurrentUser, db: DbSession, status_filter: ApplicationStatus | None = None
):
    """Owner's inbox of applications for one project."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the project owner can do this")
    stmt = (
        select(Application)
        .where(Application.project_id == project_id)
        .order_by(Application.created_at.desc())
    )
    if status_filter:
        stmt = stmt.where(Application.status == status_filter)
    return db.scalars(stmt).all()


@router.get("/applications/mine", response_model=list[ApplicationOut])
def my_applications(user: CurrentUser, db: DbSession):
    stmt = (
        select(Application)
        .where(Application.applicant_id == user.id)
        .order_by(Application.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.get("/applications/{app_id}", response_model=ApplicationOut)
def read_application(app_id: int, user: CurrentUser, db: DbSession):
    application = _get_application(db, app_id)
    if user.id not in (application.applicant_id, application.project.owner_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your application")
    return application


@router.patch("/applications/{app_id}/status", response_model=ApplicationOut)
def decide_application(
    app_id: int, payload: ApplicationStatusUpdate, user: CurrentUser, db: DbSession
):
    """Owner accepts or rejects a pending application. Accepting adds the applicant to the
    team and notifies them. If `is_payable` is true the next step is /payments (coming next)."""
    application = _get_application(db, app_id)
    project = application.project
    if project.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the project owner can do this")
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Application is already {application.status.value}"
        )

    if payload.status == ApplicationStatus.ACCEPTED:
        if application.role_id is not None:
            role = db.get(ProjectRole, application.role_id)
            filled = db.scalar(
                select(func.count(ProjectMember.id)).where(ProjectMember.role_id == role.id)
            )
            if filled >= role.slots:
                raise HTTPException(status.HTTP_409_CONFLICT, f"All '{role.title}' slots are filled")
        db.add(
            ProjectMember(
                project_id=project.id, user_id=application.applicant_id, role_id=application.role_id
            )
        )
        notification_type = NotificationType.APPLICATION_ACCEPTED
    else:
        notification_type = NotificationType.APPLICATION_REJECTED

    application.status = payload.status
    application.decided_at = datetime.now(timezone.utc)
    notify(
        db,
        application.applicant_id,
        notification_type,
        application_id=application.id,
        project_id=project.id,
        project_title=project.title,
        requires_payment=application.is_payable and payload.status == ApplicationStatus.ACCEPTED,
    )
    db.commit()
    return application


@router.post("/applications/{app_id}/withdraw", response_model=ApplicationOut)
def withdraw_application(app_id: int, user: CurrentUser, db: DbSession):
    application = _get_application(db, app_id)
    if application.applicant_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your application")
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Only pending applications can be withdrawn (is {application.status.value})"
        )
    application.status = ApplicationStatus.WITHDRAWN
    application.decided_at = datetime.now(timezone.utc)
    db.commit()
    return application
