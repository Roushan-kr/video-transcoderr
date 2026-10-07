import React, { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { Play, Pause, Volume2, VolumeX, Maximize, Settings, Check } from "lucide-react";

interface VideoPlayerProps {
  src: string;
  title?: string;
}

interface LevelOption {
  index: number;
  label: string;
  height: number;
  bitrate: number;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ src, title }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [levels, setLevels] = useState<LevelOption[]>([]);
  const [currentLevel, setCurrentLevel] = useState<number>(-1); // -1 = Auto
  const [actualHeight, setActualHeight] = useState<number>(0);
  const [showQualityMenu, setShowQualityMenu] = useState<boolean>(false);
  const [liveBitrate, setLiveBitrate] = useState<number>(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !src) return;

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      hlsRef.current = hls;

      hls.loadSource(src);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
        const qualityOptions: LevelOption[] = data.levels.map((lvl, index) => ({
          index,
          label: `${lvl.height}p`,
          height: lvl.height,
          bitrate: Math.round(lvl.bitrate / 1000),
        }));
        // Sort highest resolution first
        qualityOptions.sort((a, b) => b.height - a.height);
        setLevels(qualityOptions);
      });

      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        const lvl = hls.levels[data.level];
        if (lvl) {
          setActualHeight(lvl.height);
          setLiveBitrate(Math.round(lvl.bitrate / 1000));
        }
      });

      return () => {
        hls.destroy();
      };
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native Safari HLS
      video.src = src;
    }
  }, [src]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    videoRef.current.muted = !isMuted;
    setIsMuted(!isMuted);
  };

  const toggleFullscreen = () => {
    if (!videoRef.current) return;
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      videoRef.current.parentElement?.requestFullscreen();
    }
  };

  const handleLevelChange = (levelIndex: number) => {
    if (hlsRef.current) {
      hlsRef.current.currentLevel = levelIndex;
      setCurrentLevel(levelIndex);
      setShowQualityMenu(false);
    }
  };

  return (
    <div className="player-wrapper">
      <div className="video-container">
        <video
          ref={videoRef}
          className="video-element"
          playsInline
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onClick={togglePlay}
        />

        <div className="video-overlay-controls">
          <div className="controls-left">
            <button onClick={togglePlay} className="control-btn" title={isPlaying ? "Pause" : "Play"}>
              {isPlaying ? <Pause size={20} /> : <Play size={20} />}
            </button>
            <button onClick={toggleMute} className="control-btn" title={isMuted ? "Unmute" : "Mute"}>
              {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
            {title && <span className="video-title-display">{title}</span>}
          </div>

          <div className="controls-right">
            {/* Live ABR Info Badge */}
            <div className="metric-badge">
              <span className="live-dot" />
              <span>{actualHeight ? `${actualHeight}p` : "ABR"}</span>
              {liveBitrate > 0 && <span className="bitrate-tag">({liveBitrate} kbps)</span>}
            </div>

            {/* Quality Selector */}
            <div className="quality-dropdown-container">
              <button
                className="control-btn quality-btn"
                onClick={() => setShowQualityMenu(!showQualityMenu)}
                title="Change Stream Quality"
              >
                <Settings size={18} />
                <span>{currentLevel === -1 ? "Auto" : `${levels.find((l) => l.index === currentLevel)?.label || "Auto"}`}</span>
              </button>

              {showQualityMenu && (
                <div className="quality-menu">
                  <div className="quality-menu-header">Playback Quality</div>
                  <button
                    className={`quality-menu-item ${currentLevel === -1 ? "active" : ""}`}
                    onClick={() => handleLevelChange(-1)}
                  >
                    <span>Auto (Adaptive)</span>
                    {currentLevel === -1 && <Check size={16} />}
                  </button>
                  {levels.map((lvl) => (
                    <button
                      key={lvl.index}
                      className={`quality-menu-item ${currentLevel === lvl.index ? "active" : ""}`}
                      onClick={() => handleLevelChange(lvl.index)}
                    >
                      <span>{lvl.label} <small className="bitrate-sub">({lvl.bitrate} kbps)</small></span>
                      {currentLevel === lvl.index && <Check size={16} />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button onClick={toggleFullscreen} className="control-btn" title="Fullscreen">
              <Maximize size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
