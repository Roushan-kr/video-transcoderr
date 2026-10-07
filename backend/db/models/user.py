from sqlalchemy import TEXT, Column, Integer
from sqlalchemy.orm import relationship
from db.base import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(TEXT, nullable=False)
    email = Column(TEXT, unique=True, index=True, nullable=False)
    cognito_sub = Column(TEXT, unique=True, index=True, nullable=False)

    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")
 