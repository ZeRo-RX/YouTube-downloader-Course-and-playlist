import os
import sys
import json
import time
import threading
import traceback
import re
import urllib.parse

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yt_dlp
from colorama import init, Fore, Style


init(autoreset=True)


BASE_OUTPUT_DIR = "YouTube_Courses"
MAX_QUALITY = 1080
WORKERS = 4
SOCKET_TIMEOUT = 30
ANALYSIS_RETRIES = 2
DOWNLOAD_RETRIES = 5
FRAGMENT_RETRIES = 5
DEFAULT_QUALITY = "best"
DEFAULT_MAX_SIZE_MB = None
REQUEST_DELAY = 1.5


json_lock = threading.Lock()
analysis_start = 0
analysis_counter = 0
analysis_no_data = 0


os.makedirs(BASE_OUTPUT_DIR, exist_ok=True)


def now():
    return datetime.now().strftime("%H:%M:%S")


def log(message, color=Fore.WHITE):
    print(color + f"[{now()}] {message}" + Style.RESET_ALL, flush=True)


def format_size(size):
    if size is None:
        return "Unknown"

    try:
        size = float(size)
    except Exception:
        return "Unknown"

    units = ["B", "KB", "MB", "GB", "TB"]

    for unit in units:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} PB"


def format_duration(seconds):
    if seconds is None:
        return None

    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"
    except Exception:
        return None


def safe_filename(name):
    if not name:
        return "Unknown"

    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, "_")

    name = name.strip().rstrip(".")
    if not name:
        return "Unknown"

    return name[:180]


def title_matches_file(basename, safe_title):
    if not safe_title:
        return False

    b = basename.lower()
    if b == safe_title:
        return True

    if len(safe_title) >= 8 and b.startswith(safe_title):
        return True

    return False


def validate_youtube_url(url):
    if not url or not isinstance(url, str):
        return False

    url = url.strip()

    youtube_patterns = [
        r'^https?://(www\.)?youtube\.com/playlist\?list=[\w-]+',
        r'^https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://(www\.)?youtube\.com/shorts/[\w-]+',
        r'^https?://(www\.)?youtube\.com/live/[\w-]+',
        r'^https?://(www\.)?youtube\.com/(channel|user|c)/[\w-]+',
        r'^https?://(www\.)?youtube\.com/@[\w.-]+',
        r'^https?://youtu\.be/[\w-]+',
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return True

    return False


def load_json(path):
    if not os.path.exists(path):
        return {"playlist": {}, "settings": {}, "videos": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "playlist" not in data:
            data["playlist"] = {}
        if "settings" not in data:
            data["settings"] = {}
        if "videos" not in data:
            data["videos"] = {}

        return data
    except Exception:
        return {"playlist": {}, "settings": {}, "videos": {}}


def save_json(data, path):
    temp_path = path + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(temp_path, path)


def get_playlist_info(url):
    log("Connecting to YouTube...", Fore.CYAN)

    options = {
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "extract_flat": True,
        "socket_timeout": SOCKET_TIMEOUT,
        "retries": ANALYSIS_RETRIES,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "referer": "https://www.youtube.com/",
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        log(f"Playlist extraction failed: {e}", Fore.RED)
        return None


def get_entries(info):
    entries = info.get("entries", [])
    result = []

    for index, entry in enumerate(entries, start=1):
        if not entry:
            continue

        video_id = entry.get("id")
        if not video_id:
            continue

        url = entry.get("url")
        if not url:
            url = f"https://www.youtube.com/watch?v={video_id}"

        result.append({
            "index": index,
            "id": video_id,
            "url": url,
            "title": entry.get("title")
        })

    return result


def extract_video_info(video):
    url = video["url"]

    for attempt in range(1, ANALYSIS_RETRIES + 1):
        try:
            options = {
                "quiet": True,
                "no_warnings": True,
                "ignoreerrors": False,
                "socket_timeout": SOCKET_TIMEOUT,
                "retries": 1,
                "fragment_retries": 1,
                "skip_download": True,
                "user_agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "referer": "https://www.youtube.com/",
            }

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise RuntimeError("No information returned")

            return info
        except Exception:
            if attempt < ANALYSIS_RETRIES:
                time.sleep(attempt * 2)

    return None


def get_format_size(fmt):
    if not fmt:
        return 0
    return fmt.get("filesize") or fmt.get("filesize_approx") or 0


def get_available_qualities(info):
    qualities = {}

    for fmt in info.get("formats", []):
        vcodec = fmt.get("vcodec")
        if not vcodec or vcodec == "none":
            continue

        height = fmt.get("height")
        if not height:
            continue

        if height > MAX_QUALITY:
            continue

        size = get_format_size(fmt)
        current = qualities.get(height)

        if current is None or size > current["size"]:
            qualities[height] = {
                "height": height,
                "size": size,
                "format_id": fmt.get("format_id"),
                "ext": fmt.get("ext"),
                "fps": fmt.get("fps"),
                "vcodec": fmt.get("vcodec"),
                "tbr": fmt.get("tbr")
            }

    return qualities


def select_quality(info, requested_quality, max_size_bytes=None):
    qualities = get_available_qualities(info)
    if not qualities:
        return None

    heights = sorted(qualities.keys())

    if requested_quality == "best":
        candidates = sorted(heights, reverse=True)
    else:
        try:
            target = int(requested_quality)
        except Exception:
            target = MAX_QUALITY

        target = min(target, MAX_QUALITY)
        lower = [h for h in heights if h <= target]
        candidates = sorted(lower, reverse=True) if lower else sorted(heights)

    if max_size_bytes:
        fitting = []
        for height in candidates:
            quality = qualities[height]
            size = quality.get("size")
            if size and size <= max_size_bytes:
                fitting.append(quality)

        if fitting:
            return max(fitting, key=lambda x: x["height"])

    return qualities[candidates[0]]


def calculate_selected_size(info, selected_height):
    video_formats = []
    audio_formats = []

    for fmt in info.get("formats", []):
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        height = fmt.get("height")

        if vcodec and vcodec != "none" and height == selected_height:
            size = get_format_size(fmt)
            if size:
                video_formats.append(fmt)

        if acodec and acodec != "none" and (not vcodec or vcodec == "none"):
            size = get_format_size(fmt)
            if size:
                audio_formats.append(fmt)

    best_video = None
    if video_formats:
        best_video = max(
            video_formats,
            key=lambda x: (x.get("tbr") or x.get("vbr") or 0)
        )

    best_audio = None
    if audio_formats:
        best_audio = max(
            audio_formats,
            key=lambda x: (x.get("abr") or x.get("tbr") or 0)
        )

    video_size = get_format_size(best_video) if best_video else 0
    audio_size = get_format_size(best_audio) if best_audio else 0

    return video_size, audio_size, best_video, best_audio


def empty_video_data(video):
    return {
        "status": "no_data",
        "index": video["index"],
        "id": video["id"],
        "url": video["url"],
        "title": None,
        "channel": None,
        "duration": None,
        "duration_text": None,
        "resolution": None,
        "height": None,
        "fps": None,
        "video_format_id": None,
        "audio_format_id": None,
        "video_codec": None,
        "audio_codec": None,
        "video_size": None,
        "audio_size": None,
        "filesize": None,
        "filesize_text": None,
        "downloaded": False,
        "updated": datetime.now().isoformat()
    }


def analyze_one(video, settings):
    info = extract_video_info(video)
    if not info:
        return empty_video_data(video)

    requested_quality = settings.get("quality", DEFAULT_QUALITY)
    max_size_mb = settings.get("max_size_mb")
    max_size_bytes = float(max_size_mb) * 1024 * 1024 if max_size_mb else None

    selected = select_quality(info, requested_quality, max_size_bytes)
    if not selected:
        return empty_video_data(video)

    selected_height = selected["height"]
    video_size, audio_size, best_video, best_audio = calculate_selected_size(
        info, selected_height
    )

    total_size = video_size + audio_size
    if total_size == 0:
        total_size = selected.get("size") or 0

    title = info.get("title") or video.get("title")
    channel = info.get("channel") or info.get("uploader")

    return {
        "status": "success",
        "index": video["index"],
        "id": video["id"],
        "url": video["url"],
        "title": title,
        "channel": channel,
        "duration": info.get("duration"),
        "duration_text": format_duration(info.get("duration")),
        "resolution": f"{selected_height}p",
        "height": selected_height,
        "fps": (best_video.get("fps") if best_video else selected.get("fps")),
        "video_format_id": (
            best_video.get("format_id") if best_video else selected.get("format_id")
        ),
        "audio_format_id": (
            best_audio.get("format_id") if best_audio else None
        ),
        "video_codec": (
            best_video.get("vcodec") if best_video else selected.get("vcodec")
        ),
        "audio_codec": (
            best_audio.get("acodec") if best_audio else None
        ),
        "video_size": video_size if video_size else None,
        "audio_size": audio_size if audio_size else None,
        "filesize": total_size if total_size else None,
        "filesize_text": format_size(total_size) if total_size else None,
        "downloaded": False,
        "updated": datetime.now().isoformat()
    }


def show_analysis_progress(current, total, size, no_data):
    if total <= 0:
        return

    elapsed = time.time() - analysis_start
    speed = current / elapsed if elapsed > 0 else 0
    percent = current / total * 100
    width = 35
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)

    print(
        "\r"
        + Fore.CYAN + f"[{bar}] "
        + Fore.WHITE + f"{percent:6.2f}% "
        + f"{current}/{total} "
        + Fore.GREEN + f"| {speed:.2f}/s "
        + Fore.MAGENTA + f"| {format_size(size)} "
        + Fore.YELLOW + f"| No data: {no_data}"
        + Style.RESET_ALL,
        end="",
        flush=True
    )


def analyze_playlist(entries, data, json_path, force_update=False):
    global analysis_start, analysis_counter, analysis_no_data

    analysis_start = time.time()
    analysis_counter = 0
    analysis_no_data = 0

    settings = data.get("settings", {})
    pending = []
    total_size = 0

    for video in entries:
        old = data["videos"].get(video["id"])

        if (
            not force_update
            and old
            and old.get("status") == "success"
            and old.get("filesize") is not None
            and old.get("height") is not None
        ):
            total_size += old.get("filesize") or 0
        else:
            pending.append(video)

    log(f"Total videos: {len(entries)}", Fore.CYAN)
    log(f"Existing valid data: {len(entries) - len(pending)}", Fore.GREEN)
    log(f"Videos to analyze: {len(pending)}", Fore.YELLOW)

    if not pending:
        print()
        return total_size

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {
            executor.submit(analyze_one, video, settings): video
            for video in pending
        }

        for future in as_completed(futures):
            video = futures[future]

            try:
                result = future.result()
            except Exception:
                result = empty_video_data(video)

            with json_lock:
                data["videos"][video["id"]] = result
                save_json(data, json_path)

            analysis_counter += 1

            if result.get("status") == "no_data":
                analysis_no_data += 1
            else:
                total_size += result.get("filesize") or 0

            show_analysis_progress(
                analysis_counter, len(pending), total_size, analysis_no_data
            )

            time.sleep(REQUEST_DELAY)

    print()
    return total_size


def print_summary(data):
    videos = list(data.get("videos", {}).values())
    successful = [v for v in videos if v.get("status") == "success"]
    no_data = [v for v in videos if v.get("status") == "no_data"]

    total_size = sum(
        (v.get("filesize") or 0) for v in successful
    )

    resolutions = {}
    for video in successful:
        resolution = video.get("resolution") or "Unknown"
        resolutions[resolution] = resolutions.get(resolution, 0) + 1

    print()
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "                    PLAYLIST ANALYSIS")
    print(Fore.CYAN + "=" * 75)
    print(Fore.WHITE + f"Total videos       : {len(videos)}")
    print(Fore.GREEN + f"Successful         : {len(successful)}")
    print(Fore.YELLOW + f"No data            : {len(no_data)}")
    print(Fore.MAGENTA + f"Estimated total    : {format_size(total_size)}")
    print()

    def resolution_number(value):
        try:
            return int(value.rstrip("p"))
        except Exception:
            return 0

    print(Fore.WHITE + "Quality distribution:")
    for resolution, count in sorted(
        resolutions.items(),
        key=lambda x: resolution_number(x[0]),
        reverse=True
    ):
        print(Fore.CYAN + f"  {resolution:<10}" + Fore.WHITE + f"{count} videos")

    print(Fore.CYAN + "=" * 75)


def quality_menu(current_quality, current_limit):
    print()
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "                    QUALITY SETTINGS")
    print(Fore.CYAN + "=" * 75)
    print(Fore.WHITE + f"Current quality : {current_quality}")
    print(Fore.WHITE + "Maximum quality : 1080p")
    print(Fore.WHITE + "Maximum size    : " + (f"{current_limit} MB" if current_limit else "Unlimited"))
    print()
    print(Fore.GREEN + "[1] Best available (maximum 1080p)")
    print(Fore.GREEN + "[2] 1080p")
    print(Fore.GREEN + "[3] 720p")
    print(Fore.GREEN + "[4] 480p")
    print(Fore.GREEN + "[5] 360p")
    print(Fore.YELLOW + "[6] Custom maximum height")
    print(Fore.YELLOW + "[7] Set maximum file size")
    print(Fore.RED + "[0] Cancel")
    print(Fore.CYAN + "=" * 75)

    choice = input(Fore.WHITE + "Select: ").strip()

    quality_map = {
        "1": "best",
        "2": "1080",
        "3": "720",
        "4": "480",
        "5": "360"
    }

    if choice in quality_map:
        return quality_map[choice], current_limit

    if choice == "6":
        value = input("Enter maximum height (maximum 1080): ").strip()
        try:
            value = int(value)
            if value <= 0:
                raise ValueError
            value = min(value, MAX_QUALITY)
            return str(value), current_limit
        except Exception:
            log("Invalid quality.", Fore.RED)
            return current_quality, current_limit

    if choice == "7":
        value = input("Maximum size per video in MB (0 = unlimited): ").strip()
        try:
            value = float(value)
            if value <= 0:
                return current_quality, None
            return current_quality, value
        except Exception:
            log("Invalid size.", Fore.RED)
            return current_quality, current_limit

    return current_quality, current_limit


def update_course(course):
    data = load_json(course["json"])

    current_quality = data.get("settings", {}).get("quality", DEFAULT_QUALITY)
    current_limit = data.get("settings", {}).get("max_size_mb")

    new_quality, new_limit = quality_menu(current_quality, current_limit)

    data["settings"] = {
        "quality": new_quality,
        "max_size_mb": new_limit,
        "max_quality": MAX_QUALITY,
        "updated": datetime.now().isoformat()
    }

    save_json(data, course["json"])
    log(f"Quality set to: {new_quality}", Fore.GREEN)
    log("Re-analyzing course...", Fore.CYAN)

    info = get_playlist_info(course["url"])
    if not info:
        return

    entries = get_entries(info)
    analyze_playlist(entries, data, course["json"], force_update=True)
    print_summary(data)


def video_file_exists(folder, title):
    if not title:
        return False

    filename = safe_filename(title)
    extensions = [".mp4", ".mkv", ".webm", ".mov", ".avi"]

    for ext in extensions:
        path = os.path.join(folder, filename + ext)
        if os.path.exists(path):
            return True

    safe_name = safe_filename(title).lower()
    try:
        for f in os.listdir(folder):
            base = os.path.splitext(f)[0]
            if title_matches_file(base, safe_name):
                return True
    except Exception:
        pass

    return False


def count_downloaded_videos(course):
    data = load_json(course["json"])
    videos = data.get("videos", {})
    downloaded = 0

    media_extensions = {
        ".mp4", ".mkv", ".webm", ".mov", ".avi"
    }

    existing_files = set()

    for f in os.listdir(
        course["folder"]
    ):

        ext = os.path.splitext(
            f
        )[1].lower()

        if ext in media_extensions:

            existing_files.add(f)

    for video in videos.values():

        if video.get(
            "downloaded"
        ):

            downloaded += 1

            continue

        title = video.get("title")

        if title:

            filename = safe_filename(
                title
            )

            for ext in media_extensions:

                if filename + ext in existing_files:

                    downloaded += 1

                    break
            else:
                safe_name = safe_filename(title).lower()
                for f in existing_files:
                    base = os.path.splitext(f)[0]
                    if title_matches_file(base, safe_name):
                        downloaded += 1
                        break

    return downloaded


def create_progress_hook():
    def progress_hook(d):
        status = d.get("status")

        if status == "downloading":
            percent = d.get("_percent_str", "?")
            speed = d.get("_speed_str", "?")
            eta = d.get("_eta_str", "?")
            downloaded = d.get("downloaded_bytes")
            total = d.get("total_bytes") or d.get("total_bytes_estimate")

            print(
                "\r"
                + Fore.CYAN + percent
                + Fore.WHITE + " | "
                + format_size(downloaded) + " / " + format_size(total)
                + Fore.GREEN + f" | {speed}"
                + Fore.YELLOW + f" | ETA {eta}"
                + Style.RESET_ALL,
                end="",
                flush=True
            )

        elif status == "finished":
            print()
            log("Download finished.", Fore.GREEN)

    return progress_hook


def build_common_ydl_opts(course):
    settings = load_json(course["json"]).get("settings", {})
    quality = settings.get("quality", DEFAULT_QUALITY)

    if quality != "best":
        try:
            quality = str(min(int(quality), MAX_QUALITY))
        except Exception:
            quality = "best"

    if quality == "best":
        format_string = (
            "bestvideo[height<=1080]+bestaudio/"
            "bestvideo+bestaudio/"
            "best[height<=1080]/"
            "best"
        )
    else:
        height = min(int(quality), MAX_QUALITY)
        format_string = (
            f"bestvideo[height<={height}]+bestaudio/"
            f"bestvideo+bestaudio/"
            f"best[height<={height}]/"
            f"best"
        )

    return {
        "format": format_string,
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(course["folder"], "%(title)s.%(ext)s"),
        "nooverwrites": True,
        "continuedl": True,
        "ignoreerrors": True,
        "retries": DOWNLOAD_RETRIES,
        "fragment_retries": FRAGMENT_RETRIES,
        "socket_timeout": SOCKET_TIMEOUT,
        "noplaylist": False,
        "abort_on_error": False,
        "progress_hooks": [create_progress_hook()],
        "quiet": True,
        "no_warnings": True,
        "geo_bypass": True,
        "geo_bypass_country": "US",
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "referer": "https://www.youtube.com/",
        "sleep_interval": 2,
        "max_sleep_interval": 5,
    }, quality


def retry_failed_videos(course):
    data = load_json(course["json"])
    videos = data.get("videos", {})

    failed_videos = []

    for video_id, video in videos.items():

        if not video_file_exists(
            course["folder"],
            video.get("title")
        ):

            failed_videos.append(
                video
            )

    if not failed_videos:

        return 0

    log(
        f"Retrying "
        f"{len(failed_videos)} "
        f"failed videos...",
        Fore.YELLOW
    )

    success_count = 0

    format_selectors = [

        "bestvideo[height<=1080]+bestaudio/"
        "bestvideo+bestaudio/"
        "best[height<=1080]/"
        "best",

        "bestvideo+bestaudio",

        "best",

    ]

    geo_countries = [
        "US",
        "DE",
        "GB",
        "CA",
    ]

    for video in failed_videos:

        downloaded = False

        for geo in geo_countries:

            for fmt in format_selectors:

                retry_opts = {

                    "format": fmt,

                    "merge_output_format": "mp4",

                    "outtmpl": os.path.join(
                        course["folder"],
                        "%(title)s.%(ext)s"
                    ),

                    "ignoreerrors": True,

                    "retries": 2,

                    "fragment_retries": 2,

                    "socket_timeout": SOCKET_TIMEOUT,

                    "noplaylist": True,

                    "geo_bypass": True,

                    "geo_bypass_country": geo,

                    "user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),

                    "referer": "https://www.youtube.com/",

                    "quiet": True,

                    "no_warnings": True,

                }

                try:

                    with yt_dlp.YoutubeDL(
                        retry_opts
                    ) as ydl:

                        failed_urls = ydl.download([
                            video["url"]
                        ])

                except Exception as e:

                    failed_urls = [video["url"]]

                    log(
                        f"Retry error for "
                        f"{video.get('title')} "
                        f"[{geo}/{fmt}]: "
                        f"{str(e)[:80]}",
                        Fore.RED
                    )

                if not failed_urls and video_file_exists(
                    course["folder"],
                    video.get("title")
                ):

                    downloaded = True

                    log(
                        f"Downloaded: "
                        f"{video.get('title')} "
                        f"[{geo}/{fmt}]",
                        Fore.GREEN
                    )

                    break

                if downloaded:
                    break

            if downloaded:
                break

        if downloaded:

            success_count += 1

            video["downloaded"] = True

            video["downloaded_at"] = (
                datetime.now().isoformat()
            )

        else:

            video["permanently_failed"] = True

            log(
                f"Permanently failed: "
                f"{video.get('title')} "
                f"(all geo/format combinations failed)",
                Fore.RED
            )

        time.sleep(1)

    save_json(
        data,
        course["json"]
    )

    if success_count > 0:

        log(
            f"Auto-retry recovered "
            f"{success_count}/"
            f"{len(failed_videos)} "
            f"videos.",
            Fore.GREEN
        )

    return success_count


def download_course(course):
    data = load_json(course["json"])
    options, quality = build_common_ydl_opts(course)

    downloaded_count = count_downloaded_videos(course)
    total_count = len(data.get("videos", {}))

    print()
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "                    COURSE DOWNLOAD")
    print(Fore.CYAN + "=" * 75)
    print(Fore.WHITE + f"Course       : {course['title']}")
    print(Fore.WHITE + f"Channel      : {course['channel']}")
    print(Fore.WHITE + f"Progress     : {downloaded_count}/{total_count}")
    print(Fore.WHITE + f"Quality      : {quality}")
    print(Fore.WHITE + "Maximum      : 1080p")
    print(Fore.CYAN + "=" * 75)

    if downloaded_count >= total_count:
        log("This course is already fully downloaded.", Fore.GREEN)
        return True

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([course["url"]])
    except KeyboardInterrupt:
        print()
        log("Download interrupted by user.", Fore.YELLOW)
        return False
    except Exception:
        print()
        log("Course download error.", Fore.RED)
        traceback.print_exc()
        return False

    retry_failed_videos(course)

    time.sleep(2)

    data = load_json(course["json"])
    media_extensions = {".mp4", ".mkv", ".webm", ".mov", ".avi"}
    existing_files = set()
    try:
        for f in os.listdir(course["folder"]):
            ext = os.path.splitext(f)[1].lower()
            if ext in media_extensions:
                existing_files.add(f)
    except Exception:
        pass

    for video_id, video in data.get("videos", {}).items():
        title = video.get("title")
        if not title:
            continue

        filename = safe_filename(title)
        found = False

        for ext in media_extensions:
            if filename + ext in existing_files:
                found = True
                break

        if not found:
            safe_name = safe_filename(title).lower()
            for f in existing_files:
                if safe_name in f.lower() or f.lower().startswith(safe_name[:50]):
                    found = True
                    break

        if found:
            video["downloaded"] = True
            video["downloaded_at"] = datetime.now().isoformat()

    save_json(data, course["json"])

    final_count = count_downloaded_videos(course)
    print()

    if final_count >= total_count:
        log("Course completed successfully.", Fore.GREEN)
        return True
    else:
        log(f"Course partially downloaded: {final_count}/{total_count}", Fore.YELLOW)
        return False


def download_all_courses():
    courses = find_courses()
    if not courses:
        log("No saved courses found.", Fore.YELLOW)
        return

    pending_courses = [c for c in courses if c["status"] != "DOWNLOADED"]
    if not pending_courses:
        log("All courses are already downloaded.", Fore.GREEN)
        return

    print()
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "                    DOWNLOAD ALL")
    print(Fore.CYAN + "=" * 75)
    print(Fore.WHITE + f"Courses waiting: {len(pending_courses)}")
    print()

    for i, course in enumerate(pending_courses, start=1):
        print(Fore.WHITE + f"[{i}] {course['title']}")
        print(Fore.LIGHTBLACK_EX + f"    Channel : {course['channel']}")
        print(Fore.LIGHTBLACK_EX + f"    Videos  : {course['downloaded']}/{course['total']}")
        print(Fore.LIGHTBLACK_EX + f"    Size    : {format_size(course['size'])}")
        print(Fore.LIGHTBLACK_EX + f"    Status  : {course['status']}")
        print()

    print(Fore.CYAN + "=" * 75)
    answer = input(Fore.WHITE + "Start downloading all pending courses? [Y/N]: ").strip().lower()

    if answer not in ("y", "yes"):
        log("Download all cancelled.", Fore.YELLOW)
        return

    total_courses = len(pending_courses)
    completed_courses = 0

    for course_index, course in enumerate(pending_courses, start=1):
        print()
        print(Fore.CYAN + "=" * 75)
        print(Fore.CYAN + f"COURSE {course_index}/{total_courses}")
        print(Fore.CYAN + "=" * 75)
        print(Fore.WHITE + f"Course  : {course['title']}")
        print(Fore.WHITE + f"Channel : {course['channel']}")
        print(Fore.WHITE + f"Videos  : {course['downloaded']}/{course['total']}")
        print(Fore.WHITE + f"Size    : {format_size(course['size'])}")
        print(Fore.CYAN + "=" * 75)

        try:
            success = download_course(course)
            if success:
                completed_courses += 1

            log(
                f"Finished course {course_index}/{total_courses}.",
                Fore.GREEN if success else Fore.YELLOW
            )
        except KeyboardInterrupt:
            print()
            log("Download all interrupted by user.", Fore.YELLOW)
            break
        except Exception as e:
            print()
            log(f"Course failed: {e}", Fore.RED)
            log("Skipping to next course...", Fore.YELLOW)
            continue

    print()
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "                    DOWNLOAD ALL COMPLETE")
    print(Fore.CYAN + "=" * 75)
    print(Fore.GREEN + f"Completed courses: {completed_courses}/{total_courses}")

    remaining = find_courses()
    remaining_count = sum(1 for c in remaining if c["status"] != "DOWNLOADED")
    print(Fore.YELLOW + f"Courses remaining: {remaining_count}")
    print(Fore.CYAN + "=" * 75)


def run_download_all_noninteractive():
    courses = find_courses()
    if not courses:
        log("No saved courses found.", Fore.YELLOW)
        return

    pending_courses = [c for c in courses if c["status"] != "DOWNLOADED"]
    if not pending_courses:
        log("All courses are already downloaded.", Fore.GREEN)
        return

    log(f"Auto-download starting: {len(pending_courses)} pending courses", Fore.CYAN)

    total_courses = len(pending_courses)
    completed_courses = 0

    for course_index, course in enumerate(pending_courses, start=1):
        print()
        print(Fore.CYAN + "=" * 75)
        print(Fore.CYAN + f"AUTO COURSE {course_index}/{total_courses}")
        print(Fore.CYAN + "=" * 75)
        print(Fore.WHITE + f"Course  : {course['title']}")
        print(Fore.WHITE + f"Channel : {course['channel']}")
        print(Fore.WHITE + f"Videos  : {course['downloaded']}/{course['total']}")
        print(Fore.WHITE + f"Size    : {format_size(course['size'])}")
        print(Fore.CYAN + "=" * 75)

        try:
            success = download_course(course)
            if success:
                completed_courses += 1

            log(
                f"Finished course {course_index}/{total_courses}.",
                Fore.GREEN if success else Fore.YELLOW
            )
        except KeyboardInterrupt:
            print()
            log("Auto-download interrupted by user.", Fore.YELLOW)
            break
        except Exception as e:
            print()
            log(f"Course failed: {e}", Fore.RED)
            log("Skipping to next course...", Fore.YELLOW)
            continue

    print()
    print(Fore.CYAN + "=" * 75)
    print(Fore.CYAN + "                    AUTO DOWNLOAD COMPLETE")
    print(Fore.CYAN + "=" * 75)
    print(Fore.GREEN + f"Completed courses: {completed_courses}/{total_courses}")

    remaining = find_courses()
    remaining_count = sum(1 for c in remaining if c["status"] != "DOWNLOADED")
    print(Fore.YELLOW + f"Courses remaining: {remaining_count}")
    print(Fore.CYAN + "=" * 75)


def find_courses():
    courses = []
    if not os.path.exists(BASE_OUTPUT_DIR):
        return courses

    for folder_name in os.listdir(BASE_OUTPUT_DIR):
        folder_path = os.path.join(BASE_OUTPUT_DIR, folder_name)
        if not os.path.isdir(folder_path):
            continue

        json_path = os.path.join(folder_path, "playlist_info.json")
        if not os.path.exists(json_path):
            continue

        data = load_json(json_path)
        playlist = data.get("playlist", {})
        videos = data.get("videos", {})

        title = playlist.get("title") or folder_name
        channel = playlist.get("channel") or "Unknown Channel"
        url = playlist.get("url")
        total = len(videos)
        size = sum((v.get("filesize") or 0) for v in videos.values())

        downloaded = 0

        media_extensions = {
            ".mp4", ".mkv", ".webm", ".mov", ".avi"
        }

        existing_files = set()

        for f in os.listdir(
            folder_path
        ):

            ext = os.path.splitext(
                f
            )[1].lower()

            if ext in media_extensions:

                existing_files.add(f)

        for video in videos.values():

            if video.get(
                "downloaded"
            ):

                downloaded += 1

                continue

            video_title = video.get("title")

            if video_title:

                filename = safe_filename(
                    video_title
                )

                for ext in media_extensions:

                    if filename + ext in existing_files:

                        downloaded += 1

                        break
                else:
                    safe_name = safe_filename(video_title).lower()
                    for f in existing_files:
                        base = os.path.splitext(f)[0]
                        if title_matches_file(base, safe_name):
                            downloaded += 1
                            break

        if total == 0:
            status = "NOT DOWNLOADED"
        elif downloaded >= total:
            status = "DOWNLOADED"
        elif downloaded > 0:
            status = "IN PROGRESS"
        else:
            status = "NOT DOWNLOADED"

        courses.append({
            "title": title,
            "channel": channel,
            "url": url,
            "folder": folder_path,
            "json": json_path,
            "total": total,
            "downloaded": downloaded,
            "size": size,
            "status": status
        })

    courses.sort(key=lambda x: x["title"].lower())
    return courses


def create_new_course():
    print()
    print(Fore.CYAN + "=" * 75)

    url = input(Fore.WHITE + "Enter YouTube Playlist URL:\n> ").strip()

    if not validate_youtube_url(url):
        log("Invalid YouTube URL.", Fore.RED)
        return

    info = get_playlist_info(url)
    if not info:
        return

    title = info.get("title") or "Unknown Course"
    channel = info.get("channel") or info.get("uploader") or "Unknown Channel"
    entries = get_entries(info)

    if not entries:
        log("No videos found.", Fore.RED)
        return

    folder_name = safe_filename(f"{title} - {channel}")
    course_dir = os.path.join(BASE_OUTPUT_DIR, folder_name)
    os.makedirs(course_dir, exist_ok=True)

    json_path = os.path.join(course_dir, "playlist_info.json")
    data = load_json(json_path)

    data["playlist"] = {
        "title": title,
        "channel": channel,
        "url": url,
        "video_count": len(entries),
        "folder": os.path.abspath(course_dir),
        "max_quality": MAX_QUALITY,
        "updated": datetime.now().isoformat()
    }

    data["settings"] = {
        "quality": data.get("settings", {}).get("quality", DEFAULT_QUALITY),
        "max_size_mb": data.get("settings", {}).get("max_size_mb", DEFAULT_MAX_SIZE_MB),
        "max_quality": MAX_QUALITY,
        "updated": datetime.now().isoformat()
    }

    save_json(data, json_path)

    log(f"Course: {title}", Fore.GREEN)
    log(f"Channel: {channel}", Fore.GREEN)
    log(f"Videos: {len(entries)}", Fore.GREEN)
    log("Maximum quality: 1080p", Fore.GREEN)
    print()
    log("Starting detailed analysis...", Fore.CYAN)

    analyze_playlist(entries, data, json_path, force_update=True)
    print_summary(data)

    answer = input(Fore.WHITE + "\nStart downloading? [Y/N]: ").strip().lower()
    if answer in ("y", "yes"):
        course = {
            "title": title,
            "channel": channel,
            "folder": course_dir,
            "json": json_path,
            "url": url
        }
        download_course(course)


def course_actions(course):
    while True:
        print()
        print(Fore.CYAN + "=" * 75)
        print(Fore.CYAN + f"COURSE: {course['title']}")
        print(Fore.CYAN + "=" * 75)
        print(Fore.GREEN + "[1] Download / Continue")
        print(Fore.YELLOW + "[2] Change quality / size limit")
        print(Fore.MAGENTA + "[3] Re-analyze quality and size")
        print(Fore.WHITE + "[4] Show summary")
        print(Fore.RED + "[0] Back")
        print(Fore.CYAN + "=" * 75)

        choice = input(Fore.WHITE + "Select: ").strip()

        if choice == "0":
            break
        elif choice == "1":
            download_course(course)
        elif choice == "2":
            update_course(course)
        elif choice == "3":
            data = load_json(course["json"])
            info = get_playlist_info(course["url"])
            if info:
                entries = get_entries(info)
                analyze_playlist(entries, data, course["json"], force_update=True)
                print_summary(data)
        elif choice == "4":
            data = load_json(course["json"])
            print_summary(data)
        else:
            log("Invalid option.", Fore.RED)


def main():
    while True:
        courses = find_courses()

        print()
        print(Fore.CYAN + "=" * 75)
        print(Fore.CYAN + "                    YOUTUBE COURSE MANAGER")
        print(Fore.CYAN + "=" * 75)

        if not courses:
            print(Fore.YELLOW + "No saved courses.")

        for i, course in enumerate(courses, start=1):
            print()
            print(Fore.WHITE + f"[{i}] {course['title']}")
            print(Fore.LIGHTBLACK_EX + f"    Channel : {course['channel']}")
            print(Fore.LIGHTBLACK_EX + f"    Videos  : {course['downloaded']}/{course['total']}")
            print(Fore.LIGHTBLACK_EX + f"    Size    : {format_size(course['size'])}")

            if course["status"] == "DOWNLOADED":
                status = Fore.GREEN + "DOWNLOADED"
            elif course["status"] == "IN PROGRESS":
                status = Fore.YELLOW + f"IN PROGRESS ({course['downloaded']}/{course['total']})"
            else:
                status = Fore.RED + "NOT DOWNLOADED"

            print(Fore.WHITE + "    Status  : " + status)

        print()
        print(Fore.CYAN + "-" * 75)
        print(Fore.GREEN + "[N] Add new course")
        print(Fore.BLUE + "[D] Download all pending courses")
        print(Fore.YELLOW + "[U] Update all saved courses")
        print(Fore.RED + "[Q] Exit")
        print(Fore.CYAN + "=" * 75)

        choice = input(Fore.WHITE + "Select: ").strip().lower()

        if choice == "q":
            print()
            log("Goodbye.", Fore.CYAN)
            break

        if choice == "n":
            create_new_course()
            continue

        if choice == "d":
            download_all_courses()
            continue

        if choice == "u":
            if not courses:
                log("No courses to update.", Fore.YELLOW)
                continue

            for course in courses:
                log(f"Updating: {course['title']}", Fore.CYAN)
                data = load_json(course["json"])
                info = get_playlist_info(course["url"])
                if not info:
                    log("Could not update course.", Fore.RED)
                    continue

                entries = get_entries(info)
                analyze_playlist(entries, data, course["json"], force_update=True)
                print_summary(data)

            continue

        try:
            number = int(choice)
            if 1 <= number <= len(courses):
                course_actions(courses[number - 1])
            else:
                log("Invalid course number.", Fore.RED)
        except ValueError:
            log("Invalid option.", Fore.RED)


if __name__ == "__main__":
    try:
        print()
        print(Fore.CYAN + "=" * 75)
        print(Fore.CYAN + "                    YOUTUBE COURSE MANAGER")
        print(Fore.CYAN + "=" * 75)
        log(f"Python: {sys.version.split()[0]}", Fore.LIGHTBLACK_EX)
        log(f"yt-dlp: {yt_dlp.version.__version__}", Fore.LIGHTBLACK_EX)
        log(f"Analysis workers: {WORKERS}", Fore.LIGHTBLACK_EX)
        log("Maximum video quality: 1080p", Fore.GREEN)
        main()
    except KeyboardInterrupt:
        print()
        log("Program interrupted.", Fore.YELLOW)
    except Exception:
        print()
        log("Unexpected error:", Fore.RED)
        traceback.print_exc()
        input("\nPress Enter to exit...")
