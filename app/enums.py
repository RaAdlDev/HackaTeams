"""Enumerations shared by models and schemas. Stored as plain strings in the DB."""
import enum


class TagCategory(str, enum.Enum):
    ABILITY = "ability"      # FastAPI, React, Figma ...
    OBJECTIVE = "objective"  # Startup, Open Source, Portfolio ...
    EXPERTISE = "expertise"  # Beginner, Intermediate, Senior ...


class SkillLevel(str, enum.Enum):
    """Optional per-tag proficiency stored on UserTagLink."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ProjectStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class RewardType(str, enum.Enum):
    FLAT_FEE = "flat_fee"    # the only payable type: must run through the platform
    EQUITY = "equity"
    REV_SHARE = "rev_share"
    LEARNING = "learning"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"      # contract created, payment not yet confirmed
    HELD = "held"            # funds collected and held by the platform (escrow)
    RELEASED = "released"    # paid out to the developer
    REFUNDED = "refunded"
    FAILED = "failed"
    CANCELED = "canceled"
    DISPUTED = "disputed"


class MilestoneStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    APPROVED = "approved"


class SwipeAction(str, enum.Enum):
    LIKE = "like"
    PASS = "pass"


class NotificationType(str, enum.Enum):
    NEW_MATCH = "new_match"
    PROJECT_INTEREST = "project_interest"
    APPLICATION_RECEIVED = "application_received"
    APPLICATION_ACCEPTED = "application_accepted"
    APPLICATION_REJECTED = "application_rejected"


class PostType(str, enum.Enum):
    PROJECT_IDEA = "project_idea"
    COFOUNDER_WANTED = "cofounder_wanted"
    AVAILABILITY = "availability"
