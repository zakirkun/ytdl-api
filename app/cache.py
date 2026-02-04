import redis
import json
from typing import Optional, Dict, Any
from app.config import settings
from app.models import JobStatus, DownloadStatus, VideoInfo


class CacheManager:
    """Redis cache manager for download jobs"""
    
    def __init__(self):
        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    
    def _get_job_key(self, job_id: str) -> str:
        """Get Redis key for job"""
        return f"job:{job_id}"
    
    def _get_video_metadata_key(self, url: str) -> str:
        """Get Redis key for video metadata cache"""
        return f"metadata:{url}"
    
    def set_job_status(self, job_id: str, status: JobStatus, **kwargs) -> None:
        """Set job status with additional data"""
        key = self._get_job_key(job_id)
        data = {
            "job_id": job_id,
            "status": status.value,
            **kwargs
        }
        
        # Store as JSON with expiration (24 hours)
        self.redis_client.setex(
            key,
            86400,  # 24 hours
            json.dumps(data, default=str)
        )
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        key = self._get_job_key(job_id)
        data = self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    def update_job_progress(self, job_id: str, progress: float) -> None:
        """Update download progress"""
        job_data = self.get_job_status(job_id)
        if job_data:
            job_data["progress"] = progress
            key = self._get_job_key(job_id)
            self.redis_client.setex(key, 86400, json.dumps(job_data, default=str))
    
    def cache_video_metadata(self, url: str, metadata: Dict[str, Any], ttl: int = 3600) -> None:
        """Cache video metadata"""
        key = self._get_video_metadata_key(url)
        self.redis_client.setex(key, ttl, json.dumps(metadata))
    
    def get_cached_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached video metadata"""
        key = self._get_video_metadata_key(url)
        data = self.redis_client.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    def delete_job(self, job_id: str) -> None:
        """Delete job from cache"""
        key = self._get_job_key(job_id)
        self.redis_client.delete(key)
    
    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.redis_client.ping()
        except:
            return False


# Global cache manager instance
cache = CacheManager()
