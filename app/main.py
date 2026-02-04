from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uuid
import os
from datetime import datetime

from app.config import settings
from app.models import (
    DownloadRequest,
    DownloadResponse,
    DownloadStatus,
    HealthResponse,
    JobStatus,
    VideoInfo
)
from app.cache import cache
from app.tasks import download_video

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="YouTube Video Downloader API with background processing"
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=dict)
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    redis_connected = cache.ping()
    
    return HealthResponse(
        status="healthy" if redis_connected else "degraded",
        redis_connected=redis_connected,
        worker_active=redis_connected  # Simplified check
    )


@app.post("/api/download", response_model=DownloadResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def submit_download(request: Request, download_req: DownloadRequest):
    """
    Submit a video download request
    
    Rate limits: 10 requests per minute, 50 per hour
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Check if video metadata is cached
        cached_info = cache.get_cached_metadata(str(download_req.url))
        
        # Initialize job status
        cache.set_job_status(
            job_id,
            JobStatus.PENDING,
            url=str(download_req.url),
            quality=download_req.quality.value,
            created_at=datetime.utcnow().isoformat(),
            video_info=cached_info
        )
        
        # Queue download task
        download_video.delay(
            job_id=job_id,
            url=str(download_req.url),
            quality=download_req.quality.value
        )
        
        return DownloadResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message="Download request submitted successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit download: {str(e)}")


@app.get("/api/status/{job_id}", response_model=DownloadStatus)
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def get_download_status(request: Request, job_id: str):
    """
    Get download status for a job
    
    Rate limits: 50 requests per hour
    """
    job_data = cache.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Parse video info if exists
    video_info = None
    if job_data.get('video_info'):
        vi = job_data['video_info']
        video_info = VideoInfo(
            title=vi.get('title'),
            duration=vi.get('duration'),
            thumbnail=vi.get('thumbnail'),
            uploader=vi.get('uploader'),
            filesize=vi.get('filesize')
        )
    
    return DownloadStatus(
        job_id=job_data.get('job_id'),
        status=JobStatus(job_data.get('status')),
        progress=job_data.get('progress', 0.0),
        video_info=video_info,
        filename=job_data.get('filename'),
        error=job_data.get('error'),
        created_at=job_data.get('created_at'),
        completed_at=job_data.get('completed_at')
    )


@app.get("/api/download/{job_id}")
@limiter.limit(f"{settings.RATE_LIMIT_PER_HOUR}/hour")
async def download_file(request: Request, job_id: str):
    """
    Download the completed video file
    
    Rate limits: 50 requests per hour
    """
    job_data = cache.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job_data.get('status') != JobStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Download not ready. Current status: {job_data.get('status')}"
        )
    
    filepath = job_data.get('filepath')
    filename = job_data.get('filename')
    
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Get video title for better filename
    video_title = "video"
    if job_data.get('video_info') and job_data['video_info'].get('title'):
        video_title = job_data['video_info']['title']
        # Sanitize filename
        video_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_'))
        video_title = video_title[:100]  # Limit length
    
    return FileResponse(
        filepath,
        media_type="video/mp4",
        filename=f"{video_title}.mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{video_title}.mp4"'
        }
    )


@app.delete("/api/download/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated file
    """
    job_data = cache.get_job_status(job_id)
    
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete file if exists
    filepath = job_data.get('filepath')
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
    
    # Delete from cache
    cache.delete_job(job_id)
    
    return {"message": "Job deleted successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
