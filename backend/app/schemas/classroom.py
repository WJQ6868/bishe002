from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, conint


class ResourceStatus(str, Enum):
    in_use = "in_use"
    idle = "idle"
    maintenance = "maintenance"
    scrapped = "scrapped"
    normal = "normal"


class ClassroomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    capacity: conint(gt=0) = Field(..., description="可容纳人数")
    is_multimedia: bool = False
    code: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    devices: List[str] = Field(default_factory=list)
    status: ResourceStatus = ResourceStatus.idle
    remark: Optional[str] = Field(None, max_length=255)


class ClassroomCreate(ClassroomBase):
    pass


class ClassroomUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    capacity: Optional[conint(gt=0)] = None
    is_multimedia: Optional[bool] = None
    code: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=100)
    devices: Optional[List[str]] = None
    status: Optional[ResourceStatus] = None
    remark: Optional[str] = Field(None, max_length=255)


class ClassroomResponse(BaseModel):
    id: int
    name: str
    capacity: int
    is_multimedia: bool
    code: str
    location: Optional[str]
    devices: List[str] = Field(default_factory=list)
    status: ResourceStatus = ResourceStatus.idle
    remark: Optional[str]

    class Config:
        orm_mode = True
