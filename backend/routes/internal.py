from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from db.db import get_db
from db.models.video import Video
from sec_keys import secret_keys
from pydantic_model.video_models import VideoStatusCallbackRequest, VideoResponse

router = APIRouter()


@router.post("/videos/{video_id}/status", response_model=VideoResponse)
def update_video_status_callback(
    video_id: str,
    payload: VideoStatusCallbackRequest,
    x_internal_secret: str = Header(..., alias="X-Internal-Secret"),
    db: Session = Depends(get_db),
):
    """
    Internal authenticated webhook endpoint called by the ECS Transcoder container
    upon job completion or error.
    """
    if x_internal_secret != secret_keys.INTERNAL_API_SECRET:
        raise HTTPException(status_code=403, detail="Invalid internal webhook secret")

    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found")

    video.status = payload.status
    if payload.playback_url:
        video.playback_url = payload.playback_url
    if payload.duration is not None:
        video.duration = payload.duration
    if payload.resolutions is not None:
        video.resolutions = payload.resolutions
    if payload.error_message:
        video.error_message = payload.error_message

    db.commit()
    db.refresh(video)

    return video
