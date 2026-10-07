import React from "react";
import { Play, Clock, Sparkles, AlertTriangle, Layers } from "lucide-react";
import type { VideoItem } from "../api/client";


interface VideoGridProps {
  videos: VideoItem[];
  selectedVideoId?: string;
  onSelectVideo: (video: VideoItem) => void;
}

export const VideoGrid: React.FC<VideoGridProps> = ({
  videos,
  selectedVideoId,
  onSelectVideo,
}) => {
  if (videos.length === 0) {
    return (
      <div className="empty-catalog-state">
        <Layers size={48} className="empty-icon" />
        <h3>No videos uploaded yet</h3>
        <p>Click "Upload Video" above to trigger the S3 &rarr; SQS &rarr; ECS Fargate HLS transcoding pipeline.</p>
      </div>
    );
  }

  return (
    <div className="video-grid">
      {videos.map((video) => {
        const isSelected = video.id === selectedVideoId;
        const isReady = video.status === "READY";
        const isProcessing = video.status === "PROCESSING" || video.status === "UPLOADING" || video.status === "QUEUED";

        return (
          <div
            key={video.id}
            className={`video-card ${isSelected ? "selected" : ""} ${!isReady ? "disabled" : ""}`}
            onClick={() => isReady && onSelectVideo(video)}
          >
            <div className="thumbnail-box">
              <div className="thumbnail-gradient-bg">
                <Play size={36} className="card-play-icon" />
              </div>

              {/* Status Badge */}
              <div className={`status-pill ${video.status.toLowerCase()}`}>
                {isProcessing && <span className="pulsing-dot" />}
                {isReady && <Sparkles size={12} />}
                {video.status === "FAILED" && <AlertTriangle size={12} />}
                <span>{video.status}</span>
              </div>
            </div>

            <div className="card-content">
              <h4 className="card-title" title={video.title}>
                {video.title}
              </h4>
              {video.description && (
                <p className="card-description">{video.description}</p>
              )}

              <div className="card-footer">
                <div className="resolutions-list">
                  {video.resolutions && video.resolutions.length > 0 ? (
                    video.resolutions.map((res) => (
                      <span key={res} className="res-tag">
                        {res}
                      </span>
                    ))
                  ) : (
                    <span className="res-tag default-tag">HLS ABR</span>
                  )}
                </div>

                <div className="upload-time">
                  <Clock size={12} />
                  <span>{new Date(video.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
