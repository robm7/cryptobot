from datetime import datetime
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class StrategyBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parameters: Dict[str, str] = Field(default_factory=dict)
    version: int = Field(1, ge=1)
    is_active: bool = True

    @validator('parameters')
    def validate_parameters(cls, v):
        if not isinstance(v, dict):
            raise ValueError("Parameters must be a dictionary")
        if len(v) > 20:
            raise ValueError("Too many parameters (max 20)")
        return v

class StrategyCreate(StrategyBase):
    pass

class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parameters: Optional[Dict[str, str]] = None
    version: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None

class StrategyVersion(BaseModel):
    version: int
    created_at: datetime
    parameters: Dict[str, str]

class StrategyResponse(StrategyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    versions: List[StrategyVersion] = []

    class Config:
        orm_mode = True