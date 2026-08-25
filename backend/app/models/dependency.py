from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Dependency(Base):
    __tablename__ = "dependencies"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False, index=True)
    declared_version = Column(String, nullable=False)
    dep_type = Column(String, default="dependencies")  # dependencies, devDependencies, peerDependencies
    ecosystem = Column(String, default="npm")          # npm, pip
    manifest_path = Column(String, default="package.json")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="dependencies")
