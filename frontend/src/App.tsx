import { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar";
import { VideoPlayer } from "./components/VideoPlayer";
import { VideoGrid } from "./components/VideoGrid";
import { UploadModal } from "./components/UploadModal";
import { fetchVideos } from "./api/client";
import type { VideoItem } from "./api/client";
import { RefreshCw, PlayCircle } from "lucide-react";
import "./App.css";

// High-quality public test stream fallback for instant interview demonstrations
const DEMO_FALLBACK_STREAM = {
  id: "demo-hls-stream",
  title: "Cloud Video Transcoder — Multi-Bitrate HLS Showcase",
  description: "Synchronized closed GOP adaptive bitrate stream showcasing dynamic switching between 1080p, 720p, and 360p renditions.",
  status: "READY" as const,
  playback_url: "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
  resolutions: ["1080p", "720p", "360p"],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

export function App() {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [selectedVideo, setSelectedVideo] = useState<VideoItem>(DEMO_FALLBACK_STREAM);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  const loadVideos = async () => {
    setIsRefreshing(true);
    try {
      const data = await fetchVideos();
      if (data && data.length > 0) {
        setVideos(data);
        // If current selection is fallback or video exists in list, update or select first ready video
        const firstReady = data.find((v) => v.status === "READY" && v.playback_url);
        if (firstReady && selectedVideo.id === DEMO_FALLBACK_STREAM.id) {
          setSelectedVideo(firstReady);
        }
      } else {
        setVideos([DEMO_FALLBACK_STREAM]);
      }
    } catch (e) {
      console.warn("Could not load backend videos, showing demo stream:", e);
      setVideos([DEMO_FALLBACK_STREAM]);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadVideos();
    // Poll every 10 seconds to detect newly finished transcode jobs
    const interval = setInterval(loadVideos, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSelectVideo = (video: VideoItem) => {
    if (video.playback_url) {
      setSelectedVideo(video);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <div className="app-layout">
      <Navbar onOpenUpload={() => setIsUploadOpen(true)} videoCount={videos.length} />

      <main className="main-content">
        {/* Featured Video Player View */}
        {selectedVideo && selectedVideo.playback_url && (
          <section className="featured-player-section">
            <VideoPlayer src={selectedVideo.playback_url} title={selectedVideo.title} />

            <div className="player-info-bar">
              <div>
                <h2 className="now-playing-title">{selectedVideo.title}</h2>
                {selectedVideo.description && (
                  <p className="card-description" style={{ marginTop: "0.25rem" }}>
                    {selectedVideo.description}
                  </p>
                )}
              </div>

              <div className="hls-url-tag" title={selectedVideo.playback_url}>
                <PlayCircle size={14} style={{ display: "inline", marginRight: "4px" }} />
                <span>HLS Stream: {selectedVideo.playback_url}</span>
              </div>
            </div>
          </section>
        )}

        {/* Video Directory Grid */}
        <section className="catalog-section">
          <div className="catalog-section-header">
            <div>
              <h3 className="section-title">Transcoded Video Directory</h3>
              <p className="brand-subtitle">
                Public feed of videos transcoded into multi-bitrate HLS streams via AWS Fargate & FFmpeg
              </p>
            </div>

            <button
              onClick={loadVideos}
              className="secondary-btn"
              disabled={isRefreshing}
              style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
            >
              <RefreshCw size={14} className={isRefreshing ? "spin-icon" : ""} />
              <span>Refresh Feed</span>
            </button>
          </div>

          <VideoGrid
            videos={videos}
            selectedVideoId={selectedVideo?.id}
            onSelectVideo={handleSelectVideo}
          />
        </section>
      </main>

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploadSuccess={() => {
          loadVideos();
        }}
      />
    </div>
  );
}

export default App;
