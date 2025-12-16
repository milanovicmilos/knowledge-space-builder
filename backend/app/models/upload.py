from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Upload(Base):
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_key = Column(String(500), nullable=False, unique=True)
    file_size_bytes = Column(BigInteger, nullable=False)
    num_rows = Column(Integer)
    num_columns = Column(Integer)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
