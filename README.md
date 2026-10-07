# Distributed Cloud Video Transcoder & Adaptive Bitrate (ABR) Streaming Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![AWS ECS Fargate](https://img.shields.io/badge/AWS-ECS%20Fargate-FF9900.svg?style=flat&logo=amazonaws)](https://aws.amazon.com/fargate/)
[![Terraform](https://img.shields.io/badge/Terraform-HCL-7B42BC.svg?style=flat&logo=terraform)](https://www.terraform.io/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-ABR%20HLS-007808.svg?style=flat&logo=ffmpeg)](https://ffmpeg.org/)
[![React + Vite](https://img.shields.io/badge/React%2019-Vite%20--%20pnpm-61DAFB.svg?style=flat&logo=react)](https://react.dev/)

An event-driven, production-grade cloud-native video transcoding platform that converts high-resolution raw uploads into multi-bitrate **HLS (HTTP Live Streaming)** packages (1080p, 720p, 360p). Features direct-to-S3 presigned ingestion, asynchronous SQS queueing, serverless AWS ECS Fargate FFmpeg workers, webhooks, modular Terraform (HCL) infrastructure, and a modern React streaming client.

---

## Architecture Blueprint

```mermaid
flowchart TD
    subgraph Client["Client Layer"]
        UI["React + Vite Client (pnpm)<br/>Hls.js Player + Direct S3 Upload UI"]
    end

    subgraph BackendApp["FastAPI Backend Service"]
        AuthRouter["Cognito Auth Router<br/>/auth/signup, /auth/login, /auth/me"]
        VideoRouter["Video Router<br/>POST /videos/upload-url<br/>GET /videos<br/>GET /videos/:id"]
        WebhookRouter["Internal Webhook<br/>POST /internal/videos/:id/status"]
        DB[("PostgreSQL<br/>Users, Videos, TranscodeJobs")]
    end

    subgraph AWS["AWS Infrastructure"]
        Cognito["AWS Cognito<br/>User Pool"]
        S3Raw["S3 Raw Bucket<br/>Presigned Upload"]
        SQS["SQS Queue + DLQ"]
        Consumer["Consumer Service<br/>SQS Long Polling"]
        ECS["ECS Fargate<br/>FFmpeg Transcoder"]
        S3Processed["S3 Processed Bucket<br/>HLS .m3u8 + .ts"]
        CloudFront["CloudFront CDN<br/>HLS Delivery"]
    end

    UI -->|1. Sign in| AuthRouter
    AuthRouter <-->|Authenticate| Cognito

    UI -->|2. JWT + Request Upload URL| VideoRouter
    VideoRouter -->|Validate JWT| Cognito
    VideoRouter -->|Create Pending Video| DB
    VideoRouter -->|Presigned URL| UI

    UI -->|3. Direct PUT| S3Raw
    S3Raw -->|4. ObjectCreated| SQS
    SQS -->|5. Long Poll| Consumer
    Consumer -->|6. RunTask| ECS

    ECS -->|7. Download Raw Video| S3Raw
    ECS -->|8. FFmpeg → HLS| ECS
    ECS -->|9. Upload HLS| S3Processed
    ECS -->|10. READY / FAILED| WebhookRouter
    WebhookRouter -->|11. Update Status| DB

    UI -->|12. Fetch Catalog| VideoRouter
    UI -->|13. Request HLS| CloudFront
    CloudFront -->|Serve HLS| S3Processed
```

---

## Key System Features & Engineering Decisions

### 1. Direct-to-S3 Uploads via Presigned URLs
- **Problem**: Uploading multi-gigabyte video files directly through an application server creates memory pressure, starves HTTP thread pools, and limits concurrent user capacity.
- **Solution**: The backend signs an Amazon S3 `PUT` Presigned URL with a 60-minute expiration. The browser streams the video directly to S3 with live upload progress tracking, keeping backend servers lightweight and horizontally scalable.

### 2. Decoupled Asynchronous Transcoding (S3 &rarr; SQS &rarr; ECS Fargate)
- **Problem**: Video transcoding is compute-heavy and variable in duration (taking anywhere from seconds to tens of minutes). Monolithic or synchronous architectures suffer catastrophic cascade failures under traffic spikes.
- **Solution**: S3 emits `s3:ObjectCreated:*` notifications to an Amazon SQS queue. A dedicated consumer daemon polls SQS and triggers containerized **AWS ECS Fargate** tasks on-demand. When no videos are pending, computing resources scale to zero.

### 3. Adaptive Bitrate Streaming (ABR) with Synchronized GOP
- Generates 3 HLS quality renditions using FFmpeg:
  - **1080p (Full HD)**: 1920x1080 @ 8000 kbps (High profile, Level 4.1)
  - **720p (HD)**: 1280x720 @ 4000 kbps (High profile, Level 4.1)
  - **360p (Mobile)**: 640x360 @ 1000 kbps (Main profile)
- Synchronized closed GOP (`-g 48 -keyint_min 48 -sc_threshold 0`) ensures identical keyframe intervals across all renditions, enabling client video players to smoothly shift bitrates mid-playback without audio/video buffering or stuttering.
- Generates multi-variant `master.m3u8` playlist and independent 6-second MPEG-TS segments (`segment_%03d.ts`).

### 4. Resilient Error Handling & Dead Letter Queue (DLQ)
- SQS is configured with a Dead Letter Queue (`maxReceiveCount = 3`). Poisonous, corrupted, or unsupported media files are safely moved to the DLQ after 3 failed processing attempts without blocking the pipeline.
- Transcoder captures execution errors and notifies the backend webhook with `status="FAILED"` and error diagnostics.

### 5. Production Infrastructure as Code (Terraform / HCL)
- 100% modular AWS infrastructure defined in `terraform/`:
  - **Networking**: VPC, Public Subnets in 2 AZs, Route Tables, Internet Gateway, and ECS Security Groups.
  - **Storage**: Raw S3 bucket with CORS and SQS event notification; Processed S3 bucket with CloudFront Origin Access Control (OAC).
  - **Queueing**: SQS Queue + DLQ with Redrive policy and S3 publish permission.
  - **Compute**: ECR Repositories, ECS Fargate Cluster, Task Definitions, and least-privilege IAM Roles.
  - **Identity**: AWS Cognito User Pool with email sign-up and App Client.
  - **CDN**: Amazon CloudFront distribution with gzip/brotli compression and optimized caching headers (`no-cache` for `.m3u8`, `max-age=31536000` for `.ts` segments).

---

## Project Structure

```
video-transcoder/
├── architecture.md           # Deep-dive architecture and design documentation
├── compose.yml               # Root Docker Compose for full local orchestration
├── backend/                  # FastAPI Application
│   ├── db/                   # SQLAlchemy PostgreSQL models (User, Video)
│   ├── routes/               # API Routers (auth, videos, internal webhook)
│   ├── middleware/           # Cognito auth & session middlewares
│   ├── helper/               # S3 presigned URL generator & auth helpers
│   └── main.py               # FastAPI entry point & lifespan handler
├── transcoder/               # Worker Container (FFmpeg ABR Worker)
│   ├── main.py               # Downloader, multi-variant FFmpeg ABR, S3 uploader & webhook
│   └── Dockerfile            # Container image with Python 3.11 + FFmpeg
├── consumer/                 # SQS Polling Daemon
│   ├── main.py               # Long-polls SQS & dispatches ECS Fargate tasks
│   └── Dockerfile            # Consumer container build
├── frontend/                 # React 19 + Vite Web Application (pnpm)
│   ├── src/components/       # VideoPlayer (Hls.js + quality switcher), VideoGrid, UploadModal, Navbar
│   ├── src/api/client.ts     # S3 presigned upload & video directory client
│   └── src/App.css           # Premium dark theme design system
└── terraform/                # Infrastructure as Code (HCL)
    ├── main.tf               # Root module orchestration
    ├── variables.tf          # Parameterized inputs
    ├── outputs.tf            # Exported infrastructure endpoints
    └── modules/              # networking, storage, queue, compute, cognito, cdn
```

---

## Quickstart & Local Demonstration

### 1. Run Backend Services (Docker Compose)
Launch the PostgreSQL database, FastAPI backend, and consumer daemon locally:
```bash
docker compose up -d
```
The FastAPI backend will be live at `http://localhost:8000` with interactive Swagger docs at `http://localhost:8000/docs`.

### 2. Run the React Streaming Client
Install dependencies and launch the Vite dev server with **pnpm**:
```bash
cd frontend
pnpm install
pnpm dev
```
Open `http://localhost:5173` in your browser.
- Watch the built-in Adaptive Bitrate HLS test stream.
- Test manual quality switching between **1080p**, **720p**, and **360p**.
- Click **Upload Video** to test the direct S3 presigned upload pipeline with live progress bars.

---

## AWS Cloud Deployment (Terraform)

### Prerequisites
- AWS CLI configured (`aws configure`)
- Terraform 1.5+ installed

### Steps
1. Navigate to the terraform directory:
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   ```
2. Initialize and deploy:
   ```bash
   terraform init
   terraform plan
   terraform apply -auto-approve
   ```
3. Build and push container images to Amazon ECR:
   ```bash
   # Log in to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ECR_URL>

   # Build & push transcoder
   docker build -t <TRANSCODER_ECR_URL>:latest ./transcoder
   docker push <TRANSCODER_ECR_URL>:latest

   # Build & push consumer
   docker build -t <CONSUMER_ECR_URL>:latest ./consumer
   docker push <CONSUMER_ECR_URL>:latest
   ```

---
