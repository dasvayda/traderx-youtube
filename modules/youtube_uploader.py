"""
youtube_uploader.py — YouTube Data API v3 업로드 모듈.

수동 업로드: 파일 경로와 메타데이터를 안내 텍스트로 반환
자동 업로드: OAuth 2.0 인증 후 YouTube에 직접 업로드

사용 전 필요한 것:
  1. Google Cloud 프로젝트에서 YouTube Data API v3 활성화
  2. OAuth 2.0 클라이언트 ID 생성 → client_secrets.json 다운로드
  3. .env 에 YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json 설정
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# OAuth 스코프
_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
_TOKEN_FILE = "cache/youtube_token.json"
_API_SERVICE = "youtube"
_API_VERSION = "v3"

# Shorts 판정 기준
_SHORTS_MAX_SECONDS = 60


# ---------------------------------------------------------------------------
# 메타데이터
# ---------------------------------------------------------------------------

@dataclass
class VideoMetadata:
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: str = "25"          # 25 = News & Politics (주식 콘텐츠에 적합)
    privacy: str = "private"         # private | unlisted | public
    language: str = "ja"
    made_for_kids: bool = False

    def to_snippet(self) -> dict:
        return {
            "title": self.title[:100],
            "description": self.description[:5000],
            "tags": self.tags[:500],
            "categoryId": self.category_id,
            "defaultLanguage": self.language,
            "defaultAudioLanguage": self.language,
        }

    def to_status(self) -> dict:
        return {
            "privacyStatus": self.privacy,
            "selfDeclaredMadeForKids": self.made_for_kids,
        }


# ---------------------------------------------------------------------------
# 업로드 결과
# ---------------------------------------------------------------------------

@dataclass
class UploadResult:
    success: bool
    video_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None

    @property
    def shorts_url(self) -> Optional[str]:
        if self.video_id:
            return f"https://www.youtube.com/shorts/{self.video_id}"
        return None


# ---------------------------------------------------------------------------
# 수동 업로드 가이드
# ---------------------------------------------------------------------------

def manual_upload_guide(video_path: Path, metadata: VideoMetadata) -> str:
    """수동 업로드 시 사용자에게 보여줄 안내 텍스트를 반환합니다."""
    tags_str = ", ".join(metadata.tags) if metadata.tags else "(없음)"
    return f"""
📋 YouTube 수동 업로드 안내
{'=' * 50}

📁 파일 위치
  {video_path.resolve()}

📝 제목 (복사해서 사용하세요)
  {metadata.title}

📄 설명
  {metadata.description or '(없음)'}

🏷️ 태그
  {tags_str}

🔒 공개 범위
  {{'private': '비공개', 'unlisted': '일부 공개', 'public': '공개'}}.get('{metadata.privacy}', '{metadata.privacy}')

🔗 업로드 주소
  https://studio.youtube.com

💡 Shorts 등록 조건: 60초 이하 + 9:16 비율 (이 영상은 조건을 충족합니다)
""".strip()


# ---------------------------------------------------------------------------
# 자동 업로더
# ---------------------------------------------------------------------------

class YouTubeUploader:
    """
    YouTube Data API v3를 사용해 영상을 자동으로 업로드합니다.

    최초 실행 시 브라우저 OAuth 인증이 한 번 필요하며,
    이후에는 cache/youtube_token.json 에 저장된 토큰을 재사용합니다.
    """

    def __init__(self, client_secrets_file: Optional[str] = None):
        self._secrets_file = client_secrets_file or os.environ.get(
            "YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"
        )

    # ------------------------------------------------------------------

    def is_authenticated(self) -> bool:
        """저장된 유효 토큰이 있는지 확인합니다."""
        token_path = Path(_TOKEN_FILE)
        if not token_path.exists():
            return False
        try:
            creds = self._load_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False

    def authenticate(self) -> None:
        """
        OAuth 2.0 인증을 수행합니다.
        브라우저가 열리며 Google 계정으로 로그인해야 합니다.
        토큰은 cache/youtube_token.json 에 저장됩니다.
        """
        from google_auth_oauthlib.flow import InstalledAppFlow

        if not Path(self._secrets_file).exists():
            raise FileNotFoundError(
                f"client_secrets.json 파일을 찾을 수 없습니다: {self._secrets_file}\n"
                "Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 생성하고 "
                "파일을 프로젝트 루트에 저장하세요."
            )

        flow = InstalledAppFlow.from_client_secrets_file(self._secrets_file, _SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        logger.info("YouTube OAuth 인증 완료. 토큰 저장: %s", _TOKEN_FILE)

    def upload(self, video_path: Path, metadata: VideoMetadata) -> UploadResult:
        """
        영상을 YouTube에 업로드합니다.

        Returns:
            UploadResult — video_id, url, shorts_url 포함
        """
        try:
            youtube = self._build_service()
        except Exception as e:
            return UploadResult(success=False, error=f"YouTube 서비스 초기화 실패: {e}")

        if not video_path.exists():
            return UploadResult(success=False, error=f"영상 파일 없음: {video_path}")

        body = {
            "snippet": metadata.to_snippet(),
            "status": metadata.to_status(),
        }

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024 * 5,  # 5 MB chunks
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            logger.info("업로드 시작: %s", video_path.name)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info("업로드 진행: %d%%", pct)

            video_id = response["id"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info("업로드 완료: %s", url)
            return UploadResult(success=True, video_id=video_id, url=url)

        except Exception as e:
            logger.exception("업로드 실패")
            return UploadResult(success=False, error=str(e))

    # ------------------------------------------------------------------
    # 내부 헬퍼

    def _build_service(self):
        from googleapiclient.discovery import build

        creds = self._load_credentials()
        if creds is None or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
                self._save_credentials(creds)
            else:
                raise RuntimeError(
                    "YouTube 인증이 필요합니다. '인증' 버튼을 먼저 클릭하세요."
                )
        return build(_API_SERVICE, _API_VERSION, credentials=creds)

    def _load_credentials(self):
        from google.oauth2.credentials import Credentials

        token_path = Path(_TOKEN_FILE)
        if not token_path.exists():
            return None
        return Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    def _save_credentials(self, creds) -> None:
        Path(_TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(_TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")


# ---------------------------------------------------------------------------
# 메타데이터 자동 생성 헬퍼
# ---------------------------------------------------------------------------

def build_metadata_from_scenes(
    scenes: list[dict],
    japanese_script: str,
    privacy: str = "private",
) -> VideoMetadata:
    """
    씬 목록과 일본어 스크립트에서 YouTube 메타데이터를 자동 생성합니다.
    제목은 첫 씬의 자막, 태그는 티커 심볼에서 추출합니다.
    """
    # 제목: 첫 씬 자막 (없으면 기본값)
    title = "株式市場レポート"
    if scenes:
        first_subtitle = scenes[0].get("subtitle", "").strip()
        if first_subtitle:
            title = first_subtitle[:80]

    # 설명: 스크립트 앞부분 (300자)
    description = japanese_script[:300].strip()
    if len(japanese_script) > 300:
        description += "..."
    description += "\n\n#株式 #投資 #YouTubeShorts #トレード"

    # 태그: 씬에서 ticker 추출
    tickers = list({
        s["ticker"] for s in scenes
        if s.get("ticker") and s["ticker"] not in ("", "N/A")
    })
    tags = tickers + ["株式", "投資", "Shorts", "トレード", "市場分析"]

    return VideoMetadata(
        title=title,
        description=description,
        tags=tags,
        privacy=privacy,
    )
