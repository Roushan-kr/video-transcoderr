import React from "react";
import { Video, UploadCloud, Cpu, Radio } from "lucide-react";

interface NavbarProps {
  onOpenUpload: () => void;
  videoCount: number;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenUpload, videoCount }) => {
  return (
    <header className="navbar-header">
      <div className="navbar-container">
        <div className="brand-group">
          <div className="brand-icon-wrapper">
            <Video size={24} className="brand-icon" />
          </div>
          <div>
            <h1 className="brand-name">StreamWave</h1>
            <span className="brand-subtitle">Distributed ABR Transcoder</span>
          </div>
        </div>

        <div className="pipeline-badges-group">
          <span className="tech-badge">
            <Radio size={14} className="badge-icon-live" />
            Adaptive Bitrate (HLS)
          </span>
          <span className="tech-badge">
            <Cpu size={14} />
            ECS Fargate + SQS
          </span>
        </div>

        <div className="navbar-actions">
          <span className="count-label">Videos: {videoCount}</span>
          <button onClick={onOpenUpload} className="primary-btn upload-trigger-btn">
            <UploadCloud size={18} />
            <span>Upload Video</span>
          </button>
        </div>
      </div>
    </header>
  );
};
