[🇮🇷 فارسی](README.fa.md) | [🇬🇧 English](README.md) | [🇩🇪 Deutsch](README.de.md)

# YouTube downloader Course and playlist

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![yt-dlp](https://img.shields.io/badge/yt--dlp-2025.08.18-red)
![License](https://img.shields.io/badge/license-MIT-green)

A professional-grade YouTube course downloader and manager with auto-scheduling capabilities. Designed for downloading educational playlists with quality control, retry mechanisms, and comprehensive course tracking.

## Features

### Main Downloader (`src/youtube_downloader/downloader.py`)
- **Playlist Management**: Add, track, and manage multiple YouTube playlists
- **Quality Control**: Download up to 1080p with customizable quality settings
- **Size Limits**: Set maximum file size per video to manage storage
- **Smart Retry**: Automatic retry with geo-bypass for failed downloads
- **Progress Tracking**: Real-time download progress with speed and ETA
- **Resume Support**: Continue interrupted downloads automatically
- **Threaded Analysis**: Fast playlist analysis using multi-threading
- **JSON State Management**: Persistent course data and download status

### Auto Downloader (`src/youtube_downloader/auto_downloader.py`)
- **Scheduled Downloads**: Automatically download pending courses at a specific time
- **Interactive Time Configuration**: Prompts for target time (HH:MM) on startup
- **Non-interactive Mode**: Perfect for overnight or scheduled downloads
- **Error Handling**: Robust error handling with detailed logging

## Project Structure

```
YouTube-downloader-Course-and-playlist/
├── src/
│   └── youtube_downloader/
│       ├── __init__.py          # Public package API
│       ├── __main__.py          # `python -m youtube_downloader` entry point
│       ├── downloader.py        # Core downloader + interactive menu
│       ├── auto_downloader.py   # Scheduled auto-download script
│       └── config.py            # Shared constants & paths
├── data/                        # Runtime download output (gitignored)
│   └── [Course Name]/
│       ├── playlist_info.json
│       └── *.mp4
├── tests/
│   └── test_downloader.py       # pytest test suite
├── docs/                        # Additional documentation
├── .github/
│   └── workflows/
│       ├── tests.yml            # Multi-version pytest CI
│       └── lint.yml             # flake8 linting
├── pyproject.toml               # Build configuration (PEP 621)
├── setup.py
├── requirements.txt
├── requirements-dev.txt
├── LICENSE
├── README.md
├── README.fa.md
└── README.de.md
```

## Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg (recommended for best quality merging)

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the project as a package (registers `youtube-downloader` and `youtube-auto-downloader` console scripts):

```bash
pip install -e .
```

### Install FFmpeg (Optional but Recommended)

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

## Usage

### Interactive Mode

Run the main downloader for interactive course management:

```bash
# Recommended (from project root)
python -m youtube_downloader

# Or, if installed as a package
youtube-downloader
```

**Main Menu Options:**
1. **[N]** Add new course from YouTube playlist URL
2. **[D]** Download all pending courses
3. **[U]** Update all saved courses (re-analyze playlists)
4. **[Q]** Exit

**Course Actions:**
- **[1]** Download / Continue
- **[2]** Change quality / size limit
- **[3]** Re-analyze quality and size
- **[4]** Show summary

### Auto Download Mode

Schedule automatic downloads at a specific time:

```bash
# From project root
python -m youtube_downloader.auto_downloader

# Or, if installed as a package
youtube-auto-downloader
```

**Configuration:**
- Target time: **Entered interactively on startup** (e.g., `02:30` for 2:30 AM, `14:00` for 2:00 PM)
- Check interval: 30 seconds
- Automatically downloads all pending courses once per day at the specified time

## Configuration

### Quality Settings

The downloader supports the following quality options:
- **Best available**: Maximum 1080p (recommended)
- **1080p**: Full HD
- **720p**: HD
- **480p**: Standard Definition
- **360p**: Low bandwidth
- **Custom**: Set any maximum height (up to 1080p)

### Size Limits

You can set a maximum file size per video to manage storage:
- Example: `500 MB` - Skip videos larger than 500MB
- Set to `0` for unlimited size

## Features in Detail

### Smart Download Management
- Automatically skips already downloaded videos
- Detects existing files by title matching with **fuzzy matching fallback** (handles filename sanitization differences)
- Supports multiple video formats (.mp4, .mkv, .webm, .mov, .avi)
- **Incremental JSON state persistence**: saves each video's `downloaded` status and `downloaded_at` timestamp to `playlist_info.json` **immediately after the file finishes downloading**, so progress is never lost — even if the process is interrupted mid-playlist (critical for overnight/auto-scheduled downloads)
- A final post-download filesystem rescan reconciles any state that was missed during the live hooks

### Retry Mechanism
- Failed videos are automatically retried with different:
  - Geo-bypass regions (US, DE, GB, CA)
  - Format selectors
- Permanent failures are tracked in the JSON state

### Progress Tracking
- Real-time progress bars
- Download speed monitoring
- ETA estimation
- Total size calculation

### Data Persistence
All course data is stored in `data/[Course Name]/playlist_info.json`:
```json
{
  "playlist": {
    "title": "Course Title",
    "channel": "Channel Name",
    "url": "https://youtube.com/playlist?list=...",
    "video_count": 50,
    "folder": "path/to/course"
  },
  "settings": {
    "quality": "best",
    "max_size_mb": null,
    "max_quality": 1080
  },
  "videos": {
    "video_id": {
      "status": "success",
      "title": "Video Title",
      "duration": 600,
      "resolution": "1080p",
      "filesize": 50000000,
      "downloaded": true
    }
  }
}
```

## Security

This project:
- Does **not** collect or transmit any personal data
- Does **not** require API keys or authentication tokens
- Uses only public YouTube data through `yt-dlp`
- Stores all data locally on your machine

**Note**: The `playlist_info.json` files contain local file paths. Do not commit these files to public repositories if you want to keep your directory structure private.

## Troubleshooting

### Common Issues

**1. "Sign in to confirm you're not a bot"**
- This is a YouTube anti-bot measure
- The downloader automatically tries different regions
- For persistent issues, consider using cookies:
  ```bash
  yt-dlp --cookies-from-browser chrome "VIDEO_URL"
  ```

**2. FFmpeg not found**
- Install FFmpeg as described above
- Or use `pip install yt-dlp[ffmpeg]`

**3. Slow downloads**
- YouTube may throttle your connection
- Try downloading during off-peak hours
- Consider using a VPN

**4. Some videos fail to download**
- Videos may be geo-restricted
- Private or deleted videos will be marked as failed
- The retry mechanism will attempt multiple times

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Install dev dependencies: `pip install -r requirements-dev.txt`
4. Make your changes and add tests under `tests/`
5. Run the test suite: `pytest`
6. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

### Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Run tests with coverage
pytest --cov=youtube_downloader

# Lint
flake8 src tests --max-line-length=120
```

Continuous Integration runs on every push and pull request via GitHub Actions (`.github/workflows/tests.yml`, `.github/workflows/lint.yml`) across Python 3.8 – 3.12.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The powerful YouTube downloader library
- [colorama](https://github.com/tartley/colorama) - Cross-platform colored terminal text

## Disclaimer

This tool is for personal use only. Respect YouTube's Terms of Service and content creators' rights. Only download content you have permission to download.
