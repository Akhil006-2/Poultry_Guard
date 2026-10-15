from pydantic import BaseModel, Field
from typing import Optional, List

class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: Optional[str] = Field(default="", max_length=250)
    contact_name: Optional[str] = Field(default="", max_length=120)
    contact_phone: Optional[str] = Field(default="", max_length=50)
    notes: Optional[str] = Field(default="", max_length=2000)

class FarmUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    location: Optional[str] = Field(default=None, max_length=250)
    contact_name: Optional[str] = Field(default=None, max_length=120)
    contact_phone: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=2000)

class FlockCreate(BaseModel):
    farm_id: Optional[int] = None
    name: str = Field(min_length=1, max_length=120)
    breed: Optional[str] = Field(default="Broiler", max_length=100)
    bird_count: Optional[int] = Field(default=0, ge=0)
    age_days: Optional[int] = Field(default=0, ge=0)
    housing_type: Optional[str] = Field(default="Deep litter coop", max_length=100)
    status: Optional[str] = Field(default="active", max_length=50)

class FlockUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    breed: Optional[str] = Field(default=None, max_length=100)
    bird_count: Optional[int] = Field(default=None, ge=0)
    age_days: Optional[int] = Field(default=None, ge=0)
    housing_type: Optional[str] = Field(default=None, max_length=100)
    status: Optional[str] = Field(default=None, max_length=50)

class HealthEventCreate(BaseModel):
    farm_id: Optional[int] = None
    flock_id: Optional[int] = None
    event_date: Optional[str] = None
    signs: List[str] = []
    sick_count: int = Field(default=0, ge=0)
    deaths: int = Field(default=0, ge=0)
    feed_change: str = "unknown"
    water_change: str = "unknown"
    notes: str = Field(default="", max_length=2000)

class AlertUpdate(BaseModel):
    status: str
    dismiss_reason: Optional[str] = ""

class DensityEventUpdate(BaseModel):
    review_status: str = Field(pattern="^(pending_review|acknowledged|resolved|dismissed)$")
    notes: Optional[str] = ""

class DensitySettingsUpdate(BaseModel):
    grid_rows: int = Field(default=3, ge=2, le=4)
    grid_cols: int = Field(default=3, ge=2, le=4)
    count_threshold: int = Field(default=4, ge=1, le=50)
    area_threshold_pct: float = Field(default=10.0, ge=0.0, le=100.0)
    persistence_frames: int = Field(default=3, ge=1, le=20)
    clearing_threshold: int = Field(default=2, ge=0, le=50)
    clearing_frames: int = Field(default=2, ge=1, le=10)

class SMSTestRequest(BaseModel):
    recipient: Optional[str] = None
    message: Optional[str] = None
    dry_run: Optional[bool] = False
