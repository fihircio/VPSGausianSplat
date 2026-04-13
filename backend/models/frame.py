from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Frame(Base):
    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), index=True)
    frame_index: Mapped[int] = mapped_column(Integer, index=True)
    image_path: Mapped[str] = mapped_column(Text)
    intrinsics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pose_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    scene = relationship("Scene", back_populates="frames")
