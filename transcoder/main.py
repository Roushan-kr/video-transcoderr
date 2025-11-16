import os
from pathlib import Path
import subprocess
import boto3
from sec_keys import secret_keys


# for ABR (adaptive bitrate streaming) using HLS or DASH (MMPEG-DASH)
class VideoTranscoder:
    def __init__(self):
        self.s3_client = boto3.client(
            "s3",
            region_name=secret_keys.REGION_NAME,
            aws_access_key_id=secret_keys.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=secret_keys.AWS_SECRET_ACCESS_KEY,
        )

    def download_video(self, local_path):
        self.s3_client.download_file(
            secret_keys.S3_BUCKET_NAME, secret_keys.S3_KEY, local_path  # from docker env variable
        )

    def transcode_video(self, input_path, output_dir):
        # HLS
        CMD = [
            "ffmpeg",
            "-i",
            input_path,
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
            "v:0 v:1 v:2",
            "-hls_segment_filename",
            f"{output_dir}/%v/segment_%03d.ts",
            f"{output_dir}/%v/playlist.m3u8",
        ]
       
       #DASH
       #CMD =[]
        process = subprocess.run(CMD, shell=True, check=True)
        if process.returncode != 0:
            raise Exception("Transcoding failed")

    def _get_content_type(self, filename):
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".mp4":
            return "video/mp4"
        elif ext == ".m3u8":
            return "application/vnd.apple.mpegurl"
        elif ext == ".ts":
            return "video/MP2T"
        elif ext == ".webm":
            return "video/webm"
        else:
            return "application/octet-stream"

    def upload_files(self, prefix, local_dir):  # prefix is s3 key
        for root, _, files in os.walk(local_dir):
            for filename in files:
                local_path = os.path.join(root, filename)
                s3_path = f"{prefix}/{os.path.relpath(local_path, local_dir)}"
                self.s3_client.upload_file(
                    local_path,
                    secret_keys.AWS_S3_UPLOAD_BUCKET,
                    s3_path,
                    ExtraArgs={
                        "ACL": "public-read",
                        "ContentType": self._get_content_type(filename),
                    },
                )

    def process(self):
        work_dir = Path("/temp/workdir")
        work_dir.mkdir(exist_ok=True)
        input_video_path = work_dir / "input.mp4"
        output_dir = work_dir / "output"
        output_dir.mkdir(exist_ok=True)
        try:
            self.download_video(input_video_path)
            self.transcode_video(str(input_video_path), str(output_dir))
            self.upload_files(secret_keys.S3_KEY, str(output_dir))
        finally:
            if input_video_path.exists():
                input_video_path.unlink() 
            if output_dir.exists():
                import shutil # rmdir not work if any files inside
                shutil.rmtree(output_dir)


VideoTranscoder().process()
