from app.db.model import Base
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from datetime import datetime

class User(Base):
    __tablename__ = "user"

    uid: Mapped[str] = mapped_column(String, nullable=False) # 从 Logto 获取


    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.timezone("UTC", func.now()),
        onupdate=func.timezone("UTC", func.now()),
        nullable=False,
    )
    is_deleted: Mapped[bool] = mapped_column(default=False)
