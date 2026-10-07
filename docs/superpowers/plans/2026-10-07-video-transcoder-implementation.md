# Video Transcoder Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the video transcoder into a production-grade, resume-ready platform with direct S3 presigned uploads, decoupled SQS & ECS Fargate ABR transcoding (1080p, 720p, 360p HLS), status callbacks, Terraform (HCL) AWS infrastructure, and a modern Vite + React Hls.js streaming UI.

**Architecture:** Event-driven architecture with direct client-to-S3 presigned upload. S3 emits events to SQS; a consumer daemon triggers ECS Fargate tasks running FFmpeg multi-bitrate HLS encoding; an authenticated callback notifies the FastAPI backend which updates PostgreSQL; a React client streams HLS via Hls.js with quality switching.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, AWS SDK (Boto3), FFmpeg, Terraform (HCL), React, Vite, pnpm, Hls.js, Docker.

## Global Constraints
- Use pnpm for all frontend package management and commands.
- Python code must support environment variables with fallback defaults for local demoing.
- No hardcoded AWS credentials or subnet IDs in source code.
- FFmpeg must output synchronized GOP (keyframe) HLS segments for smooth adaptive bitrate switching.

---

### Task 1: Backend Database Models & Schemas

**Files:**
- Create: `backend/db/models/video.py`
- Modify: `backend/db/base.py`
- Create: `backend/pydantic_model/video_models.py`
- Modify: `backend/db/models/user.py`

**Interfaces:**
- Produces: `Video` model, `VideoStatus` enum (`UPLOADING`, `QUEUED`, `PROCESSING`, `READY`, `FAILED`), Pydantic models `UploadUrlRequest`, `UploadUrlResponse`, `VideoStatusCallbackRequest`, `VideoResponse`.

- [ ] **Step 1: Create Video SQLAlchemy model**
Create `backend/db/models/video.py` with fields: `id` (UUID), `user_id`, `title`, `description`, `original_s3_key`, `status`, `playback_url`, `duration`, `resolutions` (JSON), `error_message`, `created_at`, `updated_at`.

- [ ] **Step 2: Update `backend/db/base.py` to register all models**
Ensure `backend/db/base.py` imports `User` and `Video` so `Base.metadata.create_all` generates all tables.

- [ ] **Step 3: Create Pydantic schemas in `backend/pydantic_model/video_models.py`**
Define schemas for:
- `UploadUrlRequest`: title, description, filename, content_type
- `UploadUrlResponse`: video_id, upload_url, s3_key
- `VideoStatusCallbackRequest`: status, playback_url, resolutions, error_message
- `VideoResponse`: id, user_id, title, description, status, playback_url, resolutions, created_at

- [ ] **Step 4: Verify DB schema creation**
Run quick python script or command to ensure tables compile without syntax or SQLAlchemy errors.

- [ ] **Step 5: Commit**
`git add backend/db backend/pydantic_model`
`git commit -m "feat(backend): add Video database model and Pydantic schemas"`

---

### Task 2: Backend Video Management & Webhook Endpoints

**Files:**
- Create: `backend/routes/videos.py`
- Create: `backend/routes/internal.py`
- Create: `backend/helper/s3_helper.py`
- Modify: `backend/main.py`
- Modify: `backend/sec_keys.py`

**Interfaces:**
- Consumes: `Video` model, `video_models.py`, `get_current_user` middleware.
- Produces:
  - `POST /videos/upload-url` (authenticated)
  - `GET /videos` (public catalog)
  - `GET /videos/{video_id}` (public video playback details)
  - `POST /internal/videos/{video_id}/status` (internal callback secured by secret)

- [ ] **Step 1: Create S3 Helper for Presigned URLs**
Implement `backend/helper/s3_helper.py` to generate S3 Presigned PUT URLs for client uploads using `boto3`.

- [ ] **Step 2: Implement Video Routes in `backend/routes/videos.py`**
Add:
- `POST /videos/upload-url`: creates video in DB (`status=UPLOADING`), generates presigned URL, returns response.
- `GET /videos`: returns all videos with `status=READY` (or optionally all videos for the user).
- `GET /videos/{video_id}`: returns detailed metadata for a single video.

- [ ] **Step 3: Implement Internal Status Webhook in `backend/routes/internal.py`**
Add:
- `POST /internal/videos/{video_id}/status`: verifies `X-Internal-Secret` header, updates `status`, `playback_url`, `resolutions`, and `error_message`.

- [ ] **Step 4: Register new routers in `backend/main.py`**
Include `/videos` and `/internal` routers, update CORS to allow `X-Internal-Secret` and credentials.

- [ ] **Step 5: Commit**
`git add backend/`
`git commit -m "feat(backend): implement video upload presigned URL, public directory, and status callback"`

---

### Task 3: Transcoder Worker Refactoring & Callback Integration

**Files:**
- Modify: `transcoder/main.py`
- Modify: `transcoder/sec_keys.py`
- Modify: `transcoder/Dockerfile`
- Modify: `transcoder/requirements.txt`

**Interfaces:**
- Consumes: Environment variables (`S3_BUCKET_NAME`, `S3_KEY`, `VIDEO_ID`, `BACKEND_WEBHOOK_URL`, `INTERNAL_API_SECRET`, `PROCESSED_BUCKET_NAME`, `CLOUDFRONT_DOMAIN`).
- Produces: Uploaded HLS playlists & segments to S3, HTTP POST callback to `BACKEND_WEBHOOK_URL`.

- [ ] **Step 1: Update requirements in `transcoder/requirements.txt`**
Add `requests` or `httpx` for sending HTTP callbacks to backend.

- [ ] **Step 2: Refactor `transcoder/main.py`**
- Read settings from environment variables with graceful fallbacks.
- Fix FFmpeg execution (use proper argument list with `subprocess.run(..., shell=False)`).
- Generate HLS streams (1080p, 720p, 360p) with closed GOP.
- Upload `.m3u8` with `ContentType: application/vnd.apple.mpegurl` and `.ts` with `ContentType: video/MP2T`.
- On completion: compute playback URL (CloudFront or S3 URL for `master.m3u8`) and POST to backend webhook with `status="READY"`.
- On failure: catch exception and POST to backend webhook with `status="FAILED"`.
- Ensure temporary files are deleted in `finally`.

- [ ] **Step 3: Commit**
`git add transcoder/`
`git commit -m "feat(transcoder): enhance FFmpeg ABR encoding and add backend status callback"`

---

### Task 4: SQS Consumer Service Improvement

**Files:**
- Modify: `consumer/main.py`
- Modify: `consumer/sec_keys.py`
- Create: `consumer/Dockerfile`

**Interfaces:**
- Consumes: SQS messages from raw S3 bucket event notifications.
- Produces: Dispatches ECS Fargate `run_task` with container overrides (`VIDEO_ID`, `S3_BUCKET_NAME`, `S3_KEY`, `BACKEND_WEBHOOK_URL`, `INTERNAL_API_SECRET`).

- [ ] **Step 1: Refactor `consumer/main.py`**
- Dynamically read cluster name, task definition, subnets, security groups, and webhook URL from env variables.
- Extract `video_id` from the S3 key (`raw/<video_id>/<filename>`).
- Add local execution mode fallback when AWS ECS is not configured.
- Gracefully handle errors and only delete SQS messages when successfully scheduled.

- [ ] **Step 2: Add `consumer/Dockerfile`**
Create container build file for consumer service.

- [ ] **Step 3: Commit**
`git add consumer/`
`git commit -m "feat(consumer): make ECS dispatch configurable and add local execution support"`

---

### Task 5: Terraform (HCL) AWS Infrastructure as Code

**Files:**
- Create: `terraform/main.tf`
- Create: `terraform/variables.tf`
- Create: `terraform/outputs.tf`
- Create: `terraform/terraform.tfvars.example`
- Create: `terraform/modules/networking/main.tf`
- Create: `terraform/modules/storage/main.tf`
- Create: `terraform/modules/queue/main.tf`
- Create: `terraform/modules/compute/main.tf`
- Create: `terraform/modules/cognito/main.tf`
- Create: `terraform/modules/cdn/main.tf`

**Interfaces:**
- Produces: Complete AWS infrastructure provisioning:
  - VPC, Subnets, Security Groups
  - S3 Raw & Processed buckets with SQS event notification
  - SQS Queue + DLQ
  - ECS Fargate Cluster, Task Definition & ECR repositories
  - Cognito User Pool & App Client
  - CloudFront CDN distribution

- [ ] **Step 1: Create Terraform Networking Module**
VPC with DNS support, public subnets across 2 AZs, internet gateway, and security group for ECS task.

- [ ] **Step 2: Create Terraform Storage Module**
`s3_raw` bucket with CORS configuration; `s3_processed` bucket for HLS files; bucket policies.

- [ ] **Step 3: Create Terraform Queue Module**
SQS Queue with Dead Letter Queue (DLQ) and `maxReceiveCount = 3`; SQS policy granting S3 permission to publish `s3:ObjectCreated:*` events. Configure S3 bucket notification to SQS.

- [ ] **Step 4: Create Terraform Compute Module**
ECR repositories for `video-transcoder` and `video-consumer`; ECS Cluster; IAM Task Role & Task Execution Role with policies for CloudWatch logs, S3 read/write, SQS receive/delete; ECS Task Definition for Fargate.

- [ ] **Step 5: Create Terraform Cognito & CDN Modules**
Cognito User Pool with email sign-in; App Client; CloudFront distribution with S3 Processed origin, optimized cache policy, and HTTPS redirection.

- [ ] **Step 6: Root Terraform configuration & validation**
Wire root `main.tf`, `variables.tf`, `outputs.tf`, and provide a documented `terraform.tfvars.example`.

- [ ] **Step 7: Commit**
`git add terraform/`
`git commit -m "feat(infra): add complete modular Terraform (HCL) AWS infrastructure"`

---

### Task 6: Modern React + Vite Frontend (pnpm)

**Files:**
- Create: `frontend/` (Vite + React project)
- Create: `frontend/src/components/VideoPlayer.tsx`
- Create: `frontend/src/components/VideoGrid.tsx`
- Create: `frontend/src/components/UploadModal.tsx`
- Create: `frontend/src/components/Navbar.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/App.css`

**Interfaces:**
- Consumes: Backend `/videos` endpoints, S3 Presigned URL PUT upload, HLS master playlist URL.
- Produces: Interactive web UI with video streaming, quality switcher (Auto, 1080p, 720p, 360p), upload with progress bar, and video feed.

- [ ] **Step 1: Scaffold React + Vite app with pnpm**
Initialize Vite React TypeScript template in `frontend/`.

- [ ] **Step 2: Install dependencies with pnpm**
Install `hls.js`, `lucide-react`, and styling utilities.

- [ ] **Step 3: Implement Hls.js Adaptive Video Player component**
Player with playback controls, resolution selector badge (Auto, 1080p, 720p, 360p), buffer monitor, and error recovery.

- [ ] **Step 4: Implement Video Directory Grid & Upload Modal**
- Video Directory: Cards showing title, upload date, status badges (`READY`, `PROCESSING`), and click-to-play.
- Upload Modal: Select video, call `/videos/upload-url`, perform direct `fetch` PUT to S3 with `XMLHttpRequest` upload progress bar.

- [ ] **Step 5: Implement sleek UI layout and styling**
Modern dark-mode aesthetic with clean glassmorphism, responsive navigation, and status toasts.

- [ ] **Step 6: Commit**
`git add frontend/`
`git commit -m "feat(frontend): create React streaming client with HLS player and direct S3 upload"`

---

### Task 7: Docker Compose Local Orchestration & Developer Guide

**Files:**
- Create: `compose.yml` (root level)
- Create: `README.md`
- Verify: Full pipeline documentation and execution sanity check

- [ ] **Step 1: Create root `compose.yml`**
Orchestrate PostgreSQL, Backend, Consumer, and Local Transcoder for single-command local testing (`docker compose up`).

- [ ] **Step 2: Create comprehensive `README.md`**
Detailed project overview, Architecture diagram, Local run instructions, Terraform AWS deployment guide, and Resume talking points.

- [ ] **Step 3: Verification & Smoke Test**
Verify Python imports, syntax checks across all services, and frontend build check with `pnpm build`.

- [ ] **Step 4: Final commit**
`git add compose.yml README.md`
`git commit -m "docs: add root docker compose and production README"`
