from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional, Literal
from enum import Enum


class VideoQuality(str, Enum):
    """Supported video qualities"""
    Q360 = "360"
    Q480 = "480"
    Q720 = "720"
    Q1080 = "1080"


class JobStatus(str, Enum):
    """Download job status"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


class DownloadRequest(BaseModel):
    """Request model for download endpoint"""
    url: HttpUrl = Field(..., description="YouTube video URL")
    quality: VideoQuality = Field(default=VideoQuality.Q720, description="Video quality (360, 480, 720, 1080)")
    
    @field_validator('url')
    @classmethod
    def validate_youtube_url(cls, v):
        url_str = str(v)
        if not ('youtube.com' in url_str or 'youtu.be' in url_str):
            raise ValueError('Only YouTube URLs are supported')
        return v


class DownloadResponse(BaseModel):
    """Response model for download request"""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")


class VideoInfo(BaseModel):
    """Video metadata"""
    title: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    filesize: Optional[int] = None


class DownloadStatus(BaseModel):
    """Download status response"""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current status")
    progress: float = Field(default=0.0, description="Download progress (0-100)")
    video_info: Optional[VideoInfo] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    redis_connected: bool = True
    worker_active: bool = True
