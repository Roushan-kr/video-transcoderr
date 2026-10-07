# Video Transcoder Platform Design Specification

**Date:** 2026-10-07  
**Status:** Approved  
**Author:** Pair Programming Session  

---

## 1. Goal & Objectives
Elevate this video transcoding project into an end-to-end, production-grade cloud system suitable for senior engineering resume portfolios and technical interviews.

The platform provides:
1. Direct-to-S3 secure video uploads using S3 Presigned URLs.
2. Event-driven queueing with Amazon S3 and SQS.
3. Automated multi-bitrate HLS transcoding (1080p, 720p, 360p) using FFmpeg in an isolated worker container.
4. An authenticated FastAPI backend with PostgreSQL storing video metadata and processing state.
5. Internal webhook callback from transcoder to backend upon job completion or failure.
6. Public video feed and streaming detail API.
7. Modular Infrastructure as Code (Terraform / HCL) for AWS resources (VPC, S3, SQS, ECS Fargate, ECR, Cognito, CloudFront, IAM).
8. Modern React + Vite frontend client (built with pnpm) featuring Hls.js video playback, dynamic resolution selection, and video upload interface.
9. Local developer setup (Docker Compose) for demoing locally without requiring active AWS charges.

---

## 2. System Architecture & Components

### 2.1 Backend (`backend/`)
- **FastAPI Application**:
  - `routes/auth.py`: Existing Cognito signup/login/verify/refresh flow preserved and enhanced.
  - `routes/videos.py`:
    - `POST /videos/upload-url`: Requires auth. Validates video payload, generates UUID for `video_id`, creates `Video` row in DB (`status="UPLOADING"`), returns S3 Presigned PUT URL.
    - `GET /videos`: Public endpoint returning all videos with status `READY`, ordered by creation date descending.
    - `GET /videos/{video_id}`: Public endpoint returning video details, stream playback URL, available resolutions.
  - `routes/internal.py`:
    - `POST /internal/videos/{video_id}/status`: Protected by `INTERNAL_API_SECRET`. Updates video record status (`READY` or `FAILED`), playback URL, error details, and logs.
  - `db/models/video.py`: SQLAlchemy model for `videos` table (`id` UUID, `user_id`, `title`, `description`, `original_s3_key`, `status`, `playback_url`, `resolutions`, `error_message`, `created_at`, `updated_at`).
  - Configuration: Replaces hardcoded credentials with Pydantic settings loading from environment variables.

### 2.2 Transcoder Worker (`transcoder/`)
- Reads parameters from environment variables:
  - `S3_BUCKET_NAME`, `S3_KEY`, `VIDEO_ID`, `BACKEND_WEBHOOK_URL`, `INTERNAL_API_SECRET`, `PROCESSED_BUCKET_NAME`, `AWS_REGION`.
- Downloads raw video to local temp directory.
- Executes FFmpeg to generate multi-bitrate HLS streams:
  - 1080p (8000k), 720p (4000k), 360p (1000k).
  - Aligned GOP (`-g 48 -keyint_min 48 -sc_threshold 0`) and 6-second segments.
  - Master playlist `master.m3u8` and variant playlists `%v/playlist.m3u8`.
- Uploads transcoded directory to destination S3 bucket with correct MIME types (`application/vnd.apple.mpegurl` for `.m3u8`, `video/MP2T` for `.ts`).
- Notifies backend webhook:
  - Success: `POST /internal/videos/{video_id}/status` with `{ "status": "READY", "playback_url": "<cdn_or_s3_url>", "resolutions": ["360p", "720p", "1080p"] }`
  - Failure: `POST /internal/videos/{video_id}/status` with `{ "status": "FAILED", "error": "<error_message>" }`
- Cleans up temporary disk space.

### 2.3 SQS Consumer Daemon (`consumer/`)
- Long-polls Amazon SQS queue (`AWS_SQS_RAWVIDEO_QUEUE_URL`).
- Parses S3 `ObjectCreated` notification.
- Extracts `S3_BUCKET_NAME`, `S3_KEY`, and parses `video_id` from the key pattern `raw/<video_id>/<filename>`.
- Configurable execution target:
  - Cloud mode: Triggers ECS Fargate `RunTask` with task definition, passing container environment overrides.
  - Local mode: Dispatches local worker or Docker container for offline demonstrations.
- Graceful error handling and SQS message deletion upon successful task dispatch.

### 2.4 Infrastructure as Code (Terraform / HCL in `terraform/`)
- `terraform/`
  - `main.tf`: Root provider and module orchestrations.
  - `variables.tf`: Configurable parameters (region, environment, cluster specs).
  - `outputs.tf`: Exported bucket names, SQS URLs, CloudFront domain, Cognito IDs.
  - `modules/networking`: VPC, public/private subnets, security groups, IGW.
  - `modules/storage`:
    - Raw S3 bucket with CORS and SQS event notification.
    - Processed S3 bucket with CloudFront Origin Access Control (OAC) or bucket policy.
  - `modules/queue`: SQS FIFO/Standard queue + Dead Letter Queue (DLQ) with redrive policy (maxReceiveCount = 3).
  - `modules/compute`: ECR repositories, ECS Cluster, Task Definition (Fargate), IAM roles & policies.
  - `modules/cognito`: Cognito User Pool and App Client.
  - `modules/cdn`: CloudFront distribution for HLS streaming with gzip/brotli compression and optimized caching.

### 2.5 Web Frontend (`frontend/`)
- Built with **React + Vite** and initialized using **pnpm**.
- Core views & components:
  - **Video Directory Feed**: Grid displaying video cards with thumbnails/placeholders, titles, dates, and quality badges (`1080p`, `720p`, `360p`).
  - **Hls.js Player Page**: Custom video player supporting HLS adaptive bitrate streaming with manual quality switcher (Auto, 1080p, 720p, 360p) and playback controls.
  - **Upload Modal**: Simple upload form (Title, Description, File selector) that requests presigned URL from backend and uploads directly to S3 with live upload progress percentage.
  - **Auth Integration**: Lightweight login/signup dialog calling backend endpoints.

---

## 3. Error Handling & Edge Cases
- **Presigned Upload Expiration**: URLs expire after 15 minutes.
- **Transcoding Failures**: Captured in try/catch block within worker; catches FFmpeg non-zero exit codes, reports failure to backend webhook, and logs stack trace.
- **Poison Messages in SQS**: Handled by Dead Letter Queue after 3 failed attempts without stalling other jobs.
- **Disk Space Management**: Worker cleans up temporary storage in `finally` blocks regardless of job success or failure.
