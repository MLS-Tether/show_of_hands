from sqlalchemy import Column, Integer, Boolean, TIMESTAMP, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.pool import Base


class Enrollment(Base):

    __tablename__ = "enrollments"

    enrollment_id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    is_archived = Column(Boolean, nullable=False, default=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True, default=None)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    student = relationship("User", lazy="joined")
    section = relationship("Section", lazy="joined")

    __table_args__ = (
        UniqueConstraint("section_id", "student_id", name="uq_enrollment_section_student"),
    )


class EnrollmentRequest(Base):

    __tablename__ = "enrollment_requests"

    enrollment_request_id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("sections.section_id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    status = Column(Text, nullable=False, default="pending")  

    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    student = relationship("User", lazy="joined")

    __table_args__ = (
        UniqueConstraint("section_id", "student_id", name="uq_enrollment_request_section_student"),
    )