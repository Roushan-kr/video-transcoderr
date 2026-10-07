import React, { useState } from "react";
import { X, UploadCloud, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { requestUploadUrl, uploadFileToS3 } from "../api/client";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isDone, setIsDone] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.[^/.]+$/, ""));
      }
      setError(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a video file first.");
      return;
    }
    if (!title.trim()) {
      setError("Please provide a video title.");
      return;
    }

    try {
      setIsUploading(true);
      setError(null);
      setStatusMessage("Requesting secure presigned S3 URL...");

      // 1. Get Presigned S3 Upload URL
      const { upload_url } = await requestUploadUrl({
        title,
        description,
        filename: file.name,
        contentType: file.type || "video/mp4",
      });

      // 2. Direct client-to-S3 upload
      setStatusMessage("Uploading directly to Amazon S3...");
      await uploadFileToS3(upload_url, file, (percent) => {
        setProgress(percent);
      });

      setStatusMessage("Upload complete! S3 event queued for ECS Fargate transcoding.");
      setIsDone(true);
      onUploadSuccess();
    } catch (err: any) {
      console.error("Upload failed:", err);
      setError(err.message || "Failed to upload video");
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setTitle("");
    setDescription("");
    setProgress(0);
    setIsDone(false);
    setError(null);
    setStatusMessage("");
    onClose();
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <div className="modal-title">
            <UploadCloud className="modal-title-icon" size={24} />
            <h3>Direct S3 Video Upload</h3>
          </div>
          <button onClick={handleReset} className="modal-close-btn" disabled={isUploading}>
            <X size={20} />
          </button>
        </div>

        {isDone ? (
          <div className="upload-success-view">
            <CheckCircle size={56} className="success-icon" />
            <h4>Video Uploaded Successfully!</h4>
            <p>
              Your raw video is stored in S3. S3 emitted an event to Amazon SQS, which triggered the
              ECS Fargate FFmpeg worker to transcode into 1080p, 720p, and 360p HLS streams.
            </p>
            <button onClick={handleReset} className="primary-btn">
              Done & Return to Feed
            </button>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="upload-form">
            {error && (
              <div className="error-banner">
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <div className="form-group">
              <label>Select Video File (.mp4, .mov, .mkv)</label>
              <div className="file-dropzone">
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  disabled={isUploading}
                  id="video-file-input"
                />
                <label htmlFor="video-file-input" className="file-dropzone-label">
                  <UploadCloud size={32} />
                  <span>{file ? file.name : "Click or drag video here to upload"}</span>
                  {file && <small>{(file.size / (1024 * 1024)).toFixed(2)} MB</small>}
                </label>
              </div>
            </div>

            <div className="form-group">
              <label>Video Title</label>
              <input
                type="text"
                placeholder="e.g. 4K Nature Landscape Demo"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isUploading}
                required
              />
            </div>

            <div className="form-group">
              <label>Description (Optional)</label>
              <textarea
                placeholder="Brief summary of the video content..."
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isUploading}
              />
            </div>

            {isUploading && (
              <div className="progress-container">
                <div className="progress-bar-wrapper">
                  <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
                </div>
                <div className="progress-status-row">
                  <span>{statusMessage}</span>
                  <strong>{progress}%</strong>
                </div>
              </div>
            )}

            <div className="modal-actions">
              <button
                type="button"
                onClick={handleReset}
                className="secondary-btn"
                disabled={isUploading}
              >
                Cancel
              </button>
              <button type="submit" className="primary-btn" disabled={isUploading || !file}>
                {isUploading ? (
                  <>
                    <Loader2 size={18} className="spin-icon" />
                    Uploading...
                  </>
                ) : (
                  "Upload to S3 Pipeline"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
