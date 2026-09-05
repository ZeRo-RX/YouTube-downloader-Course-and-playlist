"""YouTube Course Downloader - core package."""

from .config import (
    BASE_OUTPUT_DIR,
    MAX_QUALITY,
    DEFAULT_QUALITY,
)
from .downloader import (
    mark_video_downloaded,
    video_file_exists,
    safe_filename,
    validate_youtube_url,
    run_download_all_noninteractive,
    main as interactive_main,
)

__version__ = "1.1.0"

__all__ = [
    "BASE_OUTPUT_DIR",
    "MAX_QUALITY",
    "DEFAULT_QUALITY",
    "__version__",
    "mark_video_downloaded",
    "video_file_exists",
    "safe_filename",
    "validate_youtube_url",
    "run_download_all_noninteractive",
    "interactive_main",
]