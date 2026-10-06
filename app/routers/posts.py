from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.enums import PostType
from app.models import Post, Project
from app.schemas.social import PostCreate, PostOut

router = APIRouter(prefix="/posts", tags=["ads feed"])


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(payload: PostCreate, user: CurrentUser, db: DbSession):
    """Broadcast a project idea, a co-founder search, or your availability."""
    if payload.project_id is not None:
        project = db.get(Project, payload.project_id)
        if project is None or project.owner_id != user.id:
            raise HTTPException(422, "project_id must be one of your own projects")
    post = Post(author_id=user.id, **payload.model_dump())
    db.add(post)
    db.commit()
    return post


@router.get("", response_model=list[PostOut])
def list_posts(
    user: CurrentUser,
    db: DbSession,
    type: PostType | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    """Public community board, newest first."""
    stmt = (
        select(Post)
        .where(Post.is_active.is_(True))
        .order_by(Post.created_at.desc(), Post.id.desc())
        .limit(limit)
        .offset(offset)
    )
    if type:
        stmt = stmt.where(Post.type == type)
    return db.scalars(stmt).all()


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, user: CurrentUser, db: DbSession):
    post = db.get(Post, post_id)
    if post is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Post not found")
    if post.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can delete a post")
    db.delete(post)
    db.commit()
