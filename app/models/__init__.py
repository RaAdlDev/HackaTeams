"""Import every model so Base.metadata is complete (needed by Alembic and create_all)."""
from app.models.application import Application
from app.models.payment import PaymentContract
from app.models.project import Milestone, Project, ProjectMember, ProjectRole, ProjectTagLink
from app.models.social import Message, Notification, Post, Swipe
from app.models.tag import Tag
from app.models.user import HackathonEntry, PastProject, Profile, User, UserTagLink

__all__ = [
    "Application",
    "HackathonEntry",
    "Message",
    "Milestone",
    "Notification",
    "PastProject",
    "PaymentContract",
    "Post",
    "Profile",
    "Project",
    "ProjectMember",
    "ProjectRole",
    "ProjectTagLink",
    "Swipe",
    "Tag",
    "User",
    "UserTagLink",
]
