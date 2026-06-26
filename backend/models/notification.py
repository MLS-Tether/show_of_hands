from sqlalchemy import Column
from db.pool import Base


class Notification(Base):
    __tablename__ = "notifications"
