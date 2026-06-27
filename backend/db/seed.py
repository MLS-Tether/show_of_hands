from db.pool import SessionLocal
from models.class__model import Class_

DEFAULT_CLASSES = [
    "Algebra",
    "Geometry",
    "Calculus",
    "Biology",
    "Chemistry",
    "Physics",
    "English Literature",
    "Creative Writing",
    "US History",
    "World History",
    "Economics",
    "Psychology",
    "Computer Science",
    "Art",
    "Music Theory",
    "Physical Education",
    "Spanish",
    "French",
    "Mandarin",
]


def seed_classes():
    db = SessionLocal()
    try:
        if db.query(Class_).count() == 0:
            for name in DEFAULT_CLASSES:
                db.add(Class_(name=name))
            db.commit()
    finally:
        db.close()
