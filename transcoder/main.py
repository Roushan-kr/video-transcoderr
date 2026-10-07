import os
import logging
import tempfile
import subprocess
from pathlib import Path
import boto3
from botocore.config import Config
import requests

from sec_keys import secret_keys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VideoTranscoder")


class VideoTranscoder:
    def __init__(self):
        s3_kwargs = {
            "region_name": secret_keys.REGION_NAME or "us-east-1",
            "config": Config(signature_version="s3v4"),
        }
        if secret_keys.AWS_ACCESS_KEY_ID and secret_keys.AWS_SECRET_ACCESS_KEY:
            s3_kwargs["aws_access_key_id"] = secret_keys.AWS_ACCESS_KEY_ID
            s3_kwargs["aws_secret_access_key"] = secret_keys.AWS_SECRET_ACCESS_KEY
        if secret_keys.AWS_ENDPOINT_URL:
            s3_kwargs["endpoint_url"] = secret_keys.AWS_ENDPOINT_URL

        self.s3_client = boto3.client("s3", **s3_kwargs)

    def download_video(self, bucket: str, key: str, local_path: Path):
        logger.info(f"Downloading s3://{bucket}/{key} -> {local_path}")
        self.s3_client.download_file(bucket, key, str(local_path))
        logger.info(f"Downloaded video ({local_path.stat().st_size} bytes)")

    def transcode_video(self, input_path: str, output_dir: str):
        """
        Transcode input video into multi-bitrate HLS streams:
        - 1080p @ 8000k
        - 720p  @ 4000k
        - 360p  @ 1000k
        with 6-second segments and master playlist.
        """
        logger.info("Starting FFmpeg Adaptive Bitrate (ABR) HLS transcoding...")

        for res in ["360p", "720p", "1080p"]:
            (Path(output_dir) / res).mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(input_path),
            "-filter_complex",
            "[0:v]split=3[v1][v2][v3];"
            "[v1]scale=640:360:flags=fast_bilinear[360p];"
            "[v2]scale=1280:720:flags=fast_bilinear[720p];"
            "[v3]scale=1920:1080:flags=fast_bilinear[1080p]",
            "-map",
            "[360p]",
            "-map",
            "[720p]",
            "-map",
            "[1080p]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-g",
            "48",
            "-keyint_min",
            "48",
            "-sc_threshold",
            "0",
            "-b:v:0",
            "1000k",
            "-b:v:1",
            "4000k",
            "-b:v:2",
            "8000k",
            "-f",
            "hls",
            "-hls_time",
            "6",
            "-hls_playlist_type",
            "vod",
            "-hls_flags",
            "independent_segments",
            "-hls_segment_type",
            "mpegts",
            "-hls_list_size",
            "0",
            "-master_pl_name",
            "master.m3u8",
            "-var_stream_map",
            "v:0,name:360p v:1,name:720p v:2,name:1080p",
            "-hls_segment_filename",
            os.path.join(output_dir, "%v", "segment_%03d.ts"),
            os.path.join(output_dir, "%v", "playlist.m3u8"),
        ]

        logger.info(f"Executing FFmpeg command...")
        process = subprocess.run(cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if process.returncode != 0:
            error_output = process.stderr.decode("utf-8", errors="replace")[-1000:]
            logger.error(f"FFmpeg failed with exit code {process.returncode}: {error_output}")
            raise RuntimeError(f"FFmpeg transcoding failed: {error_output}")

        logger.info("FFmpeg transcoding completed successfully.")

    def _get_content_type(self, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".mp4":
            return "video/mp4"
        elif ext == ".m3u8":
            return "application/vnd.apple.mpegurl"
        elif ext == ".ts":
            return "video/MP2T"
        elif ext == ".webm":
            return "video/webm"
        return "application/octet-stream"

    def upload_files(self, upload_bucket: str, prefix: str, local_dir: str):
        logger.info(f"Uploading transcoded HLS files to s3://{upload_bucket}/{prefix}...")
        count = 0
        for root, _, files in os.walk(local_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                rel_path = os.path.relpath(local_path, local_dir).replace("\\", "/")
                s3_path = f"{prefix}/{rel_path}"

                extra_args = {
                    "ContentType": self._get_content_type(filename),
                    "CacheControl": "max-age=31536000, public" if filename.endswith(".ts") else "no-cache",
                }

                self.s3_client.upload_file(local_path, upload_bucket, s3_path, ExtraArgs=extra_args)
                count += 1

        logger.info(f"Successfully uploaded {count} files to s3://{upload_bucket}/{prefix}")

    def notify_backend(self, video_id: str, status: str, playback_url: str = None, error_message: str = None):
        webhook_url = f"{secret_keys.BACKEND_WEBHOOK_URL.rstrip('/')}/internal/videos/{video_id}/status"
        payload = {
            "status": status,
            "playback_url": playback_url,
            "resolutions": ["360p", "720p", "1080p"] if status == "READY" else None,
            "error_message": error_message,
        }
        headers = {
            "X-Internal-Secret": secret_keys.INTERNAL_API_SECRET,
            "Content-Type": "application/json",
        }

        logger.info(f"Notifying backend status for video {video_id} -> {status} at {webhook_url}")
        try:
            res = requests.post(webhook_url, json=payload, headers=headers, timeout=15)
            logger.info(f"Backend webhook responded: {res.status_code}")
        except Exception as e:
            logger.error(f"Failed to notify backend webhook: {e}")

    def process(self):
        bucket = secret_keys.S3_BUCKET_NAME
        key = secret_keys.S3_KEY
        upload_bucket = secret_keys.AWS_S3_UPLOAD_BUCKET or bucket

        if not bucket or not key:
            logger.error("Missing required S3_BUCKET_NAME or S3_KEY environment variables.")
            return

        # Extract video_id from env or S3 key (raw/<video_id>/<filename>)
        video_id = secret_keys.VIDEO_ID
        if not video_id:
            parts = key.split("/")
            if len(parts) >= 3 and parts[0] == "raw":
                video_id = parts[1]
            else:
                video_id = os.path.splitext(os.path.basename(key))[0]

        logger.info(f"Starting processing for video_id={video_id}, s3://{bucket}/{key}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            input_video_path = work_dir / "input.mp4"
            output_dir = work_dir / "output"
            output_dir.mkdir(exist_ok=True)

            try:
                # 1. Download
                self.download_video(bucket, key, input_video_path)

                # 2. Transcode
                self.transcode_video(str(input_video_path), str(output_dir))

                # 3. Upload
                prefix = f"processed/{video_id}"
                self.upload_files(upload_bucket, prefix, str(output_dir))

                # 4. Determine playback URL
                if secret_keys.CLOUDFRONT_DOMAIN:
                    playback_url = f"https://{secret_keys.CLOUDFRONT_DOMAIN}/{prefix}/master.m3u8"
                else:
                    playback_url = f"https://{upload_bucket}.s3.{secret_keys.REGION_NAME}.amazonaws.com/{prefix}/master.m3u8"

                # 5. Callback success
                self.notify_backend(video_id, "READY", playback_url=playback_url)
                logger.info(f"Video transcoding workflow finished successfully. Playback: {playback_url}")

            except Exception as e:
                logger.exception("Transcoding job failed:")
                self.notify_backend(video_id, "FAILED", error_message=str(e))
                raise


if __name__ == "__main__":
    VideoTranscoder().process()
