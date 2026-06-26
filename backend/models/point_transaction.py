from sqlalchemy import Column
from db.pool import Base


class PointTransaction(Base):
    __tablename__ = "point_transactions"
