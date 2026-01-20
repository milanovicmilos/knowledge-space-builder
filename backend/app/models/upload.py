from sqlalchemy import Column, Integer, String, DateTime, BigInteger
from sqlalchemy.sql import func
from app.database import Base


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # stored filename
    original_filename = Column(String, nullable=False, server_default="")
    storage_key = Column(String, nullable=False)
    file_size_bytes = Column(BigInteger)
    num_rows = Column(Integer)
    num_columns = Column(Integer)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
