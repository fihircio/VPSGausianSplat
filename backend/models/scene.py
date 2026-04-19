from datetime import datetime
from typing import List

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="UPLOADED")
    input_type: Mapped[str] = mapped_column(String(16))  # image | video
    input_path: Mapped[str] = mapped_column(Text)
    frames_dir: Mapped[str] = mapped_column(Text)
    sparse_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    splat_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    faiss_index_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    feature_meta_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress_percent: Mapped[float] = mapped_column(default=0.0)
    current_task_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    frames: Mapped[List["Frame"]] = relationship(back_populates="scene", cascade="all, delete-orphan")
    feature_sets: Mapped[List["FeatureSet"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )
    anchors: Mapped[List["Anchor"]] = relationship(
        back_populates="scene", cascade="all, delete-orphan"
    )
