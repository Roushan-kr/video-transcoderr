from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class UploadUrlRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    filename: str = Field(..., min_length=1)
    content_type: str = Field(default="video/mp4")


class UploadUrlResponse(BaseModel):
    video_id: str
    upload_url: str
    s3_key: str
    bucket: str


class VideoStatusCallbackRequest(BaseModel):
    status: str = Field(..., pattern="^(READY|FAILED|PROCESSING)$")
    playback_url: Optional[str] = None
    duration: Optional[float] = None
    resolutions: Optional[List[str]] = None
    error_message: Optional[str] = None


class VideoResponse(BaseModel):
    id: str
    user_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str
    playback_url: Optional[str] = None
    duration: Optional[float] = None
    resolutions: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
