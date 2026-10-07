# Distributed Video Transcoding & Adaptive Bitrate (ABR) Streaming Platform

An event-driven, production-grade cloud-native video transcoding pipeline with Adaptive Bitrate Streaming (HLS), Amazon Web Services (AWS) Infrastructure as Code (Terraform / HCL), FastAPI backend, and modern React streaming client.

---

## 1. System Architecture Overview

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        UI["React + Vite Web App (pnpm)<br/>Hls.js Video Player + Upload UI"]
    end

    subgraph BackendApp ["FastAPI Backend Service"]
        AuthRouter["Cognito Auth Router<br/>/auth/signup, /auth/login, /auth/me"]
        VideoRouter["Video Router<br/>POST /videos/upload-url<br/>GET /videos (Public Directory)<br/>GET /videos/:id"]
        WebhookRouter["Internal Webhook Router<br/>POST /internal/videos/:id/status"]
        DB[(PostgreSQL Database<br/>Users, Videos, TranscodeJobs)]
    end

    subgraph AWS_Infra ["AWS Cloud Infrastructure (Terraform / HCL)"]
        S3Raw["S3 Raw Ingestion Bucket<br/>(Client Direct Presigned Upload)"]
        SQS["Amazon SQS Queue + DLQ<br/>(S3 ObjectCreated Event Notification)"]
        ConsumerService["Consumer Service<br/>(SQS Long Polling Daemon)"]
        ECS["Amazon ECS Fargate<br/>(FFmpeg Video Transcoder Task)"]
        S3Processed["S3 Processed Bucket<br/>(HLS .m3u8 playlists + .ts chunks)"]
        CloudFront["CloudFront CDN<br/>(Global Low-Latency HLS Delivery)"]
        Cognito["AWS Cognito User Pool<br/>(JWT Identity & Auth)"]
    end

    UI -->|1. Sign in & authenticate| AuthRouter
    UI -->|2. Request Presigned Upload URL| VideoRouter
    VideoRouter -->|Create Pending Record| DB
    UI -->|3. Direct PUT Upload| S3Raw
    S3Raw -->|4. s3:ObjectCreated:* Event| SQS
    SQS -->|5. Poll & Receive Message| ConsumerService
    ConsumerService -->|6. ECS RunTask with Env Overrides| ECS
    ECS -->|7. Download Raw Video| S3Raw
    ECS -->|8. Transcode to HLS (360p, 720p, 1080p)| ECS
    ECS -->|9. Upload HLS Master + Segments| S3Processed
    ECS -->|10. Status Callback: READY/FAILED| WebhookRouter
    WebhookRouter -->|11. Update Video Status & HLS URL| DB
    UI -->|12. Fetch Public Video Directory| VideoRouter
    UI -->|13. Stream ABR HLS Video| CloudFront
```

---

## 2. Core Architectural Pillars

### A. Direct-to-S3 Ingestion via Presigned URLs
- **Problem Solved**: Streaming multi-gigabyte video uploads directly through application servers exhausts memory, ties up HTTP worker threads, and creates costly scaling bottlenecks.
- **Solution**: The backend issues a cryptographically signed Amazon S3 Presigned URL (`PUT`). The browser uploads directly to S3. Backend stays stateless and lightweight.

### B. Decoupled Event-Driven Pipeline (S3 &rarr; SQS &rarr; ECS)
- **Problem Solved**: Video transcoding is CPU/memory intensive and variable in duration (seconds to tens of minutes). Synchronous or monolithic processing causes cascading failures.
- **Solution**: S3 automatically notifies an Amazon SQS queue. A dedicated consumer service polls SQS and dispatches isolated **AWS ECS Fargate** tasks on-demand. If tasks fail, messages route to a Dead Letter Queue (DLQ) after retries.

### C. Adaptive Bitrate Streaming (ABR) with HLS
- **FFmpeg Transcoding Pipeline**:
  - **1080p (Full HD)**: 1920x1080 @ 8000 kbps (High profile, Level 4.1)
  - **720p (HD)**: 1280x720 @ 4000 kbps (High profile, Level 4.1)
  - **360p (Mobile/Low Bandwidth)**: 640x360 @ 1000 kbps (Main profile)
- **HLS Packaging**:
  - Independent 6-second MPEG-TS segments (`segment_%03d.ts`).
  - Closed GOP (Group of Pictures) with consistent 48-frame keyframe intervals to guarantee smooth rendition switching without audio/video drift.
  - Generates variant playlists (`playlist.m3u8`) and root `master.m3u8`.

### D. Global CDN Edge Delivery
- Amazon CloudFront delivers HLS master playlists and TS chunks from S3 Processed bucket.
- Configured with optimized caching headers (`max-age=2` for dynamic/live playlists, `max-age=31536000` for immutable TS segments) and CORS headers.

---

## 3. Database Schema (PostgreSQL)

### `users` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PRIMARY KEY | Unique user ID |
| `name` | TEXT | NOT NULL | User's full name |
| `email` | TEXT | UNIQUE, NOT NULL | User's email |
| `cognito_sub` | TEXT | UNIQUE, NOT NULL | Cognito Subject Identifier |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Account creation date |

### `videos` Table
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | UUID | PRIMARY KEY | Unique video UUID |
| `user_id` | INT | FOREIGN KEY (users.id) | Video creator |
| `title` | VARCHAR(255) | NOT NULL | Video title |
| `description` | TEXT | NULLABLE | Video description |
| `original_s3_key` | TEXT | NOT NULL | Path in S3 raw bucket |
| `status` | VARCHAR(50) | NOT NULL | `UPLOADING`, `QUEUED`, `PROCESSING`, `READY`, `FAILED` |
| `playback_url` | TEXT | NULLABLE | CloudFront/S3 master.m3u8 URL |
| `duration` | FLOAT | NULLABLE | Video length in seconds |
| `resolutions` | JSONB | NULLABLE | Available qualities `["360p", "720p", "1080p"]` |
| `error_message` | TEXT | NULLABLE | Transcoding failure details if any |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Timestamp of upload request |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last status update timestamp |

---

## 4. API Endpoints Specification

### Authentication (`/auth`)
- `POST /auth/signup`: Register user with Cognito & local DB.
- `POST /auth/login`: Authenticate with Cognito, set secure HTTP-only cookies.
- `POST /auth/verify`: Confirm email verification code.
- `POST /auth/me`: Fetch authenticated user profile.

### Video Management (`/videos`)
- `POST /videos/upload-url`:
  - **Auth**: Required
  - **Body**: `{ "title": "My Video", "description": "Demo video", "filename": "sample.mp4", "content_type": "video/mp4" }`
  - **Response**: `{ "video_id": "uuid", "upload_url": "https://s3.amazonaws.com/...", "s3_key": "raw/uuid/sample.mp4" }`
- `GET /videos`:
  - **Auth**: Public
  - **Response**: List of videos with status `READY`, including `title`, `playback_url`, `resolutions`, and author.
- `GET /videos/{video_id}`:
  - **Auth**: Public
  - **Response**: Detailed video playback metadata.

### Internal Webhook (`/internal/videos/{video_id}/status`)
- `POST /internal/videos/{video_id}/status`:
  - **Auth**: Shared internal secret token (`X-Internal-Secret`)
  - **Body**: `{ "status": "READY" | "FAILED", "playback_url": "...", "resolutions": ["360p", "720p", "1080p"], "error": null }`
  - Updates DB record and unlocks video for public streaming.

---

## 5. Infrastructure as Code (Terraform / HCL)

The infrastructure is defined under `terraform/` with modular structure:
1. `modules/networking`: VPC, Public/Private subnets, Internet Gateway, Security Groups.
2. `modules/storage`:
   - `s3_raw`: Ingestion bucket with CORS and SQS event notification.
   - `s3_processed`: Output bucket with public/CloudFront read policy.
3. `modules/queue`: SQS Queue, SQS Dead Letter Queue (DLQ), Redrive policy.
4. `modules/compute`:
   - ECR repositories for transcoder & consumer images.
   - ECS Cluster + Task Definitions (CPU: 2048, Memory: 4096 for FFmpeg Fargate).
   - IAM Task Execution and Task Roles with least-privilege S3/SQS permissions.
5. `modules/auth`: AWS Cognito User Pool & App Client with secret hash.
6. `modules/cdn`: CloudFront distribution pointing to `s3_processed` with HTTPS and optimized caching.

---

## 6. Resume & Interview Talking Points

1. **Scalability & Cost Efficiency**:
   - Used S3 presigned URLs so backend memory and network bandwidth are not consumed by client uploads.
   - Transcoding tasks run on AWS Fargate serverless containers—scaling to zero when no videos are in the queue, eliminating idle server expenses.
2. **Resilience & Fault Tolerance**:
   - SQS decouples ingestion spikes from transcoding capacity.
   - Added SQS Dead Letter Queue (DLQ) to isolate poisonous or corrupted video files without halting the pipeline.
3. **Adaptive Bitrate Streaming (ABR)**:
   - Configured multi-variant HLS encoding in FFmpeg with synchronized keyframe intervals (`-g 48 -keyint_min 48`), enabling players to switch seamlessly between 360p, 720p, and 1080p based on real-time client bandwidth.
4. **Clean Code & Security**:
   - Least-privilege IAM roles; no hardcoded AWS credentials in code.
   - Containerized microservices (FastAPI backend, SQS consumer daemon, FFmpeg worker).
   - Complete Terraform IaC allowing one-command deployment and teardown of the entire cloud stack.
