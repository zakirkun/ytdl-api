from celery import Celery
from celery.schedules import crontab
from datetime import datetime, timedelta
import os
import logging
from app.config import settings
from app.cache import cache
from app.downloader import VideoDownloader
from app.models import JobStatus

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    'ytdl_worker',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'app.tasks.cleanup_old_files',
        'schedule': crontab(minute=f'*/{settings.CLEANUP_INTERVAL_MINUTES}'),
    },
}


@celery_app.task(bind=True, max_retries=3)
def download_video(self, job_id: str, url: str, quality: str):
    """
    Background task to download YouTube video
    
    Args:
        job_id: Unique job identifier
        url: YouTube video URL
        quality: Video quality (360, 480, 720, 1080)
    """
    try:
        logger.info(f"Starting download for job {job_id}: {url}")
        
        # Update status to downloading
        cache.set_job_status(
            job_id,
            JobStatus.DOWNLOADING,
            progress=0.0,
            created_at=datetime.utcnow().isoformat()
        )
        
        # Progress callback
        def progress_callback(percentage: float):
            cache.update_job_progress(job_id, round(percentage, 2))
            logger.info(f"Job {job_id}: {percentage:.2f}%")
        
        # Create downloader
        downloader = VideoDownloader(quality=quality, progress_callback=progress_callback)
        
        # Get video info first and cache it
        video_info = downloader.get_video_info(url)
        cache.cache_video_metadata(url, video_info)
        
        # Download video
        result = downloader.download(url)
        
        # Update status to completed
        cache.set_job_status(
            job_id,
            JobStatus.COMPLETED,
            progress=100.0,
            filename=result['filename'],
            filepath=result['filepath'],
            video_info={
                'title': result['title'],
                'duration': result['duration'],
                'filesize': result['filesize'],
                'thumbnail': video_info.get('thumbnail'),
                'uploader': video_info.get('uploader'),
            },
            completed_at=datetime.utcnow().isoformat(),
            created_at=datetime.utcnow().isoformat()
        )
        
        logger.info(f"Job {job_id} completed successfully: {result['filename']}")
        return {'status': 'success', 'filename': result['filename']}
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        
        # Update status to failed
        cache.set_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e),
            completed_at=datetime.utcnow().isoformat()
        )
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@celery_app.task
def cleanup_old_files():
    """
    Periodic task to cleanup old downloaded files
    Removes files older than FILE_RETENTION_HOURS
    """
    try:
        download_dir = settings.DOWNLOAD_DIR
        if not os.path.exists(download_dir):
            return
        
        now = datetime.now()
        retention_delta = timedelta(hours=settings.FILE_RETENTION_HOURS)
        deleted_count = 0
        
        for filename in os.listdir(download_dir):
            filepath = os.path.join(download_dir, filename)
            
            # Skip if not a file
            if not os.path.isfile(filepath):
                continue
            
            # Get file modification time
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            
            # Delete if older than retention period
            if now - file_mtime > retention_delta:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    logger.info(f"Deleted old file: {filename}")
                except Exception as e:
                    logger.error(f"Failed to delete {filename}: {str(e)}")
        
        logger.info(f"Cleanup completed. Deleted {deleted_count} files.")
        return {'deleted_count': deleted_count}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise
