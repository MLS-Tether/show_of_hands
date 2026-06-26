from sqlalchemy import Column
from db.pool import Base


class HelpRequest(Base):
    __tablename__ = "help_requests"
