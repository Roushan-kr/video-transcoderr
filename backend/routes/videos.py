import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.db import get_db
from db.models.video import Video
from db.models.user import User
from middleware.auth_middleware import get_optional_current_user
from helper.s3_helper import generate_presigned_upload_url
from sec_keys import secret_keys
from pydantic_model.video_models import (
    UploadUrlRequest,
    UploadUrlResponse,
    VideoResponse,
)

router = APIRouter()


@router.post("/upload-url", response_model=UploadUrlResponse)
def get_upload_url(
    payload: UploadUrlRequest,
    db: Session = Depends(get_db),
    user_info: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Generate an S3 presigned URL for direct client-to-S3 video upload,
    and create an initial pending video record in PostgreSQL.
    """
    video_id = str(uuid.uuid4())
    sanitized_filename = payload.filename.replace(" ", "_")
    s3_key = f"raw/{video_id}/{sanitized_filename}"

    # Associate with user if authenticated
    db_user_id = None
    if user_info and "sub" in user_info:
        user = db.query(User).filter(User.cognito_sub == user_info["sub"]).first()
        if user:
            db_user_id = user.id

    try:
        upload_url = generate_presigned_upload_url(
            bucket_name=secret_keys.RAW_S3_BUCKET_NAME,
            object_key=s3_key,
            content_type=payload.content_type,
            expires_in=3600,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")

    new_video = Video(
        id=video_id,
        user_id=db_user_id,
        title=payload.title,
        description=payload.description,
        original_s3_key=s3_key,
        status="UPLOADING",
        resolutions=[],
    )
    db.add(new_video)
    db.commit()
    db.refresh(new_video)

    return UploadUrlResponse(
        video_id=video_id,
        upload_url=upload_url,
        s3_key=s3_key,
        bucket=secret_keys.RAW_S3_BUCKET_NAME,
    )


@router.get("", response_model=List[VideoResponse])
def list_videos(
    status: Optional[str] = Query(None, description="Filter by status (e.g. READY, UPLOADING, PROCESSING)"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Public directory of videos. By default returns all READY videos,
    or filters by status if provided.
    """
    query = db.query(Video)
    if status:
        query = query.filter(Video.status == status)
    else:
        # Default to READY for public feed, but include all if requested
        query = query.filter(Video.status.in_(["READY", "PROCESSING"]))

    videos = query.order_by(desc(Video.created_at)).limit(limit).all()
    return videos


@router.get("/{video_id}", response_model=VideoResponse)
def get_video_by_id(video_id: str, db: Session = Depends(get_db)):
    """
    Retrieve specific video details and HLS playback URL.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
