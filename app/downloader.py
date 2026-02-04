import yt_dlp
import os
from typing import Dict, Any, Callable, Optional
from app.config import settings


class VideoDownloader:
    """YouTube video downloader using yt-dlp"""
    
    def __init__(self, quality: str = "720", progress_callback: Optional[Callable] = None):
        self.quality = quality
        self.progress_callback = progress_callback
        self.download_dir = settings.DOWNLOAD_DIR
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
    
    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """Progress hook for yt-dlp"""
        if self.progress_callback and d['status'] == 'downloading':
            # Calculate percentage
            if d.get('total_bytes'):
                percentage = (d.get('downloaded_bytes', 0) / d['total_bytes']) * 100
            elif d.get('total_bytes_estimate'):
                percentage = (d.get('downloaded_bytes', 0) / d['total_bytes_estimate']) * 100
            else:
                percentage = 0
            
            self.progress_callback(percentage)
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """Get video metadata without downloading"""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'filesize': info.get('filesize') or info.get('filesize_approx'),
                'description': info.get('description'),
                'view_count': info.get('view_count'),
            }
    
    def download(self, url: str) -> Dict[str, Any]:
        """Download video and return file info"""
        
        # Format selection based on quality
        # Best video with specified height + best audio, merged to mp4
        format_str = f'bestvideo[height<={self.quality}][ext=mp4]+bestaudio[ext=m4a]/best[height<={self.quality}][ext=mp4]/best'
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'no_warnings': True,
            'quiet': False,
            'no_color': True,
            # Merge to mp4
            'merge_output_format': 'mp4',
            # Post-processing
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            # File size limit
            'max_filesize': settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get the actual filename after download
            filename = ydl.prepare_filename(info)
            # Replace extension with mp4 (after post-processing)
            if not filename.endswith('.mp4'):
                base = os.path.splitext(filename)[0]
                filename = base + '.mp4'
            
            return {
                'filename': os.path.basename(filename),
                'filepath': filename,
                'title': info.get('title'),
                'duration': info.get('duration'),
                'filesize': os.path.getsize(filename) if os.path.exists(filename) else None,
            }
