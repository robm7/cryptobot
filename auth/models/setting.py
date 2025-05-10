from sqlalchemy import Column, String, Text, Boolean
from database import Base

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(255), primary_key=True, index=True)
    value = Column(Text)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    is_editable = Column(Boolean, default=True)