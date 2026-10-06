"""Seed the controlled tag vocabulary. Idempotent: safe to run repeatedly.

    python -m app.seed
"""
from sqlalchemy import select

from app.database import SessionLocal
from app.enums import TagCategory
from app.models import Tag
from app.services.tags import slugify

SEED: dict[TagCategory, list[str]] = {
    TagCategory.ABILITY: [
        "Python", "FastAPI", "Django", "Flask", "JavaScript", "TypeScript", "React", "Next.js",
        "Vue", "Node.js", "Go", "Rust", "Java", "C#", "C++", "Swift", "Kotlin", "Flutter",
        "PostgreSQL", "MongoDB", "Redis", "Docker", "Kubernetes", "AWS", "GraphQL",
        "Machine Learning", "Data Science", "Solidity", "Figma", "UI/UX Design",
        "Product Management", "DevOps", "Cybersecurity", "Game Development",
    ],
    TagCategory.OBJECTIVE: [
        "Startup", "Open Source", "Portfolio", "Learning", "Hackathon", "Side Project", "Freelance",
    ],
    TagCategory.EXPERTISE: ["Beginner", "Intermediate", "Advanced", "Expert"],
}


def seed() -> int:
    created = 0
    with SessionLocal() as db:
        for category, names in SEED.items():
            for name in names:
                slug = slugify(name)
                exists = db.scalar(
                    select(Tag.id).where(Tag.category == category, Tag.slug == slug)
                )
                if not exists:
                    db.add(Tag(name=name, slug=slug, category=category))
                    created += 1
        db.commit()
    return created


if __name__ == "__main__":
    print(f"Created {seed()} new tags")
