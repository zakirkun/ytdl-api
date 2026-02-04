# YouTube Downloader API

Production-ready YouTube video downloader dengan FastAPI, yt-dlp, Redis caching, Celery workers, Docker, dan Nginx.

## ✨ Features

- 🎥 Download YouTube videos dengan berbagai kualitas (360p, 480p, 720p, 1080p)
- 🚀 Background processing dengan Celery workers
- ⚡ Redis caching untuk metadata video
- 🔄 Auto-cleanup file temporary
- 🛡️ Rate limiting untuk public access
- 📊 Real-time progress tracking
- 🐳 Docker deployment ready
- 🔧 Nginx reverse proxy

## 📋 Requirements

- Docker & Docker Compose
- Minimal 2GB RAM
- 10GB storage untuk temporary files

## 🚀 Quick Start

### 1. Clone Repository

```bash
cd workarea/ytdl
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env jika diperlukan (optional)
```

### 3. Build dan Run

```bash
# Build dan start semua services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 4. Akses API

- **API**: http://localhost
- **API Docs**: http://localhost/docs
- **Health Check**: http://localhost/api/health

## 📖 API Documentation

### Submit Download Request

```bash
POST /api/download
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "quality": "720"
}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "pending",
  "message": "Download request submitted successfully"
}
```

### Check Download Status

```bash
GET /api/status/{job_id}
```

**Response:**
```json
{
  "job_id": "uuid-here",
  "status": "downloading",
  "progress": 65.5,
  "video_info": {
    "title": "Video Title",
    "duration": 242,
    "thumbnail": "https://...",
    "uploader": "Channel Name",
    "filesize": 15728640
  },
  "filename": "video_id.mp4",
  "error": null,
  "created_at": "2024-02-04T12:00:00",
  "completed_at": null
}
```

### Download File

```bash
GET /api/download/{job_id}
```

Returns video file dengan filename yang sudah di-sanitize.

### Delete Job

```bash
DELETE /api/download/{job_id}
```

Menghapus job dan file yang terkait.

## 🎯 Video Quality Options

- `360` - 360p (SD)
- `480` - 480p (SD)
- `720` - 720p (HD) - **Default**
- `1080` - 1080p (Full HD)

## 🔧 Configuration

Edit `.env` file untuk mengubah konfigurasi:

```bash
# File retention (berapa lama file disimpan)
FILE_RETENTION_HOURS=2

# Cleanup interval
CLEANUP_INTERVAL_MINUTES=30

# Rate limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=50

# Max file size (MB)
MAX_FILE_SIZE_MB=500

# Worker concurrency
CELERY_WORKER_CONCURRENCY=4
```

## 🏗️ Architecture

```
┌─────────────┐
│   Nginx     │ :80 (Reverse Proxy)
└──────┬──────┘
       │
┌──────▼──────┐
│   FastAPI   │ :8000 (Web API)
└──────┬──────┘
       │
┌──────▼──────┐     ┌──────────────┐
│    Redis    │◄────┤ Celery Worker│
└─────────────┘     └──────────────┘
       ▲
       │
┌──────┴──────┐
│ Celery Beat │ (Periodic Tasks)
└─────────────┘
```

### Services:

- **nginx**: Reverse proxy, load balancing, static files
- **web**: FastAPI application
- **worker**: Celery worker untuk download tasks
- **beat**: Celery beat untuk scheduled cleanup
- **redis**: Cache dan message broker

## 📊 Monitoring

### Check Service Status

```bash
# All services
docker-compose ps

# Specific service logs
docker-compose logs -f web
docker-compose logs -f worker
docker-compose logs -f beat
```

### Health Check

```bash
curl http://localhost/api/health
```

## 🛠️ Development

### Local Development (tanpa Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (via Docker)
docker run -d -p 6379:6379 redis:7-alpine

# Setup environment
export REDIS_URL=redis://localhost:6379/0
export DOWNLOAD_DIR=./downloads
mkdir -p downloads

# Run FastAPI
uvicorn app.main:app --reload --port 8000

# Run Celery Worker (terminal baru)
celery -A app.tasks.celery_app worker --loglevel=info

# Run Celery Beat (terminal baru)
celery -A app.tasks.celery_app beat --loglevel=info
```

## 🔒 Production Deployment

### 1. Update Nginx Configuration

Untuk production, update `nginx/nginx.conf`:
- Tambahkan SSL/TLS certificate
- Set proper server_name
- Tambahkan security headers

### 2. Resource Limits

Edit `docker-compose.yml` untuk menambahkan resource limits:

```yaml
services:
  web:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
```

### 3. Environment Variables

Gunakan proper production values di `.env`:
- Set DEBUG=False
- Update RATE_LIMIT sesuai kebutuhan
- Set FILE_RETENTION_HOURS sesuai storage capacity

### 4. Backup & Monitoring

- Setup log aggregation (ELK stack, etc)
- Monitor disk usage untuk folder downloads
- Setup alerts untuk failed jobs

## 🐛 Troubleshooting

### Worker tidak memproses jobs

```bash
# Restart worker
docker-compose restart worker

# Check worker logs
docker-compose logs -f worker
```

### Redis connection error

```bash
# Check Redis status
docker-compose ps redis

# Restart Redis
docker-compose restart redis
```

### File tidak terdownload

1. Check disk space: `df -h`
2. Check permissions pada folder `downloads`
3. Check worker logs untuk detailed error

### Rate limit exceeded

Wait beberapa saat atau tingkatkan rate limit di `.env`.

## 📝 Notes

- Download folder akan di-cleanup setiap 30 menit (configurable)
- Files akan dihapus setelah 2 jam (configurable)
- Maximum file size adalah 500MB (configurable)
- Semua format akan di-convert ke MP4

## 🤝 Contributing

Feel free to open issues atau pull requests!

## 📄 License

MIT License
