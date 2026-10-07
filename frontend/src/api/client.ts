export interface VideoItem {
  id: string;
  user_id?: number | null;
  title: string;
  description?: string | null;
  status: "UPLOADING" | "QUEUED" | "PROCESSING" | "READY" | "FAILED";
  playback_url?: string | null;
  duration?: number | null;
  resolutions?: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface UploadUrlResponse {
  video_id: string;
  upload_url: string;
  s3_key: string;
  bucket: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchVideos(): Promise<VideoItem[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/videos`);
    if (!res.ok) {
      throw new Error(`Failed to fetch videos: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    console.error("API error fetching videos:", err);
    return [];
  }
}

export async function fetchVideoById(videoId: string): Promise<VideoItem | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/videos/${videoId}`);
    if (!res.ok) return null;
    return await res.json();
  } catch (err) {
    console.error("API error fetching video details:", err);
    return null;
  }
}

export async function requestUploadUrl(data: {
  title: string;
  description?: string;
  filename: string;
  contentType: string;
}): Promise<UploadUrlResponse> {
  const res = await fetch(`${API_BASE_URL}/videos/upload-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: data.title,
      description: data.description,
      filename: data.filename,
      content_type: data.contentType,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate presigned upload URL");
  }

  return await res.json();
}

export function uploadFileToS3(
  uploadUrl: string,
  file: File,
  onProgress: (percent: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl, true);
    xhr.setRequestHeader("Content-Type", file.type || "video/mp4");

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new Error(`S3 upload failed with status ${xhr.status}: ${xhr.statusText}`));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during S3 upload"));
    xhr.send(file);
  });
}
