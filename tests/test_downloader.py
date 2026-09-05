"""Tests for the youtube_downloader package."""
import json
import os
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from youtube_downloader import downloader
from youtube_downloader.downloader import (
    mark_video_downloaded,
    safe_filename,
    title_matches_file,
    validate_youtube_url,
    video_file_exists,
)


def _make_course(tmpdir, videos):
    folder = os.path.join(tmpdir, "CourseX")
    os.makedirs(folder, exist_ok=True)
    json_path = os.path.join(folder, "playlist_info.json")
    data = {
        "playlist": {"title": "CourseX", "channel": "Ch", "url": "u"},
        "settings": {"quality": "best"},
        "videos": videos,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return {"folder": folder, "json": json_path}


def test_mark_video_downloaded_by_id(tmp_path):
    course = _make_course(str(tmp_path), {
        "VID1": {"status": "success", "title": "Episode 1", "downloaded": False},
        "VID2": {"status": "success", "title": "Episode 2", "downloaded": False},
    })

    mark_video_downloaded(course["json"], "VID1", None)

    with open(course["json"], encoding="utf-8") as f:
        updated = json.load(f)

    assert updated["videos"]["VID1"]["downloaded"] is True
    assert "downloaded_at" in updated["videos"]["VID1"]
    assert updated["videos"]["VID2"]["downloaded"] is False


def test_mark_video_downloaded_by_title_fallback(tmp_path):
    course = _make_course(str(tmp_path), {
        "VIDX": {"status": "success", "title": "Some Lecture", "downloaded": False},
    })

    mark_video_downloaded(course["json"], None, "Some Lecture")

    with open(course["json"], encoding="utf-8") as f:
        updated = json.load(f)

    assert updated["videos"]["VIDX"]["downloaded"] is True


def test_mark_video_downloaded_idempotent(tmp_path):
    course = _make_course(str(tmp_path), {
        "VID1": {"status": "success", "title": "Ep 1", "downloaded": False},
    })

    mark_video_downloaded(course["json"], "VID1", None)
    with open(course["json"], encoding="utf-8") as f:
        first_ts = json.load(f)["videos"]["VID1"]["downloaded_at"]

    time.sleep(0.01)
    mark_video_downloaded(course["json"], "VID1", None)
    with open(course["json"], encoding="utf-8") as f:
        second_ts = json.load(f)["videos"]["VID1"]["downloaded_at"]

    assert first_ts == second_ts, "Second call should not overwrite timestamp"


def test_progress_hook_marks_video_on_finished(tmp_path):
    course = _make_course(str(tmp_path), {
        "ABC123": {"status": "success", "title": "Lesson One", "downloaded": False},
    })

    hook = downloader.create_progress_hook(course)
    hook({"status": "finished", "info_dict": {"id": "ABC123", "title": "Lesson One"}})

    with open(course["json"], encoding="utf-8") as f:
        updated = json.load(f)

    assert updated["videos"]["ABC123"]["downloaded"] is True


def test_video_file_exists_basic(tmp_path):
    folder = str(tmp_path)
    open(os.path.join(folder, "My Lesson.mp4"), "wb").close()
    assert video_file_exists(folder, "My Lesson") is True
    assert video_file_exists(folder, "Not There") is False


def test_video_file_exists_fuzzy(tmp_path):
    folder = str(tmp_path)
    open(os.path.join(folder, "Lecture 01 Intro.mp4"), "wb").close()
    assert video_file_exists(folder, "Lecture 01 Intro") is True


def test_safe_filename_strips_invalid_chars():
    assert '<' not in safe_filename('a<b>c')
    assert safe_filename('a<b>c') == 'a_b_c'


def test_validate_youtube_url_accepts_valid():
    assert validate_youtube_url("https://www.youtube.com/playlist?list=ABC")
    assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ")


def test_validate_youtube_url_rejects_invalid():
    assert not validate_youtube_url("https://example.com/foo")
    assert not validate_youtube_url("")


def test_title_matches_file_true_for_prefix():
    assert title_matches_file("Intro Lesson", "intro lesson") is True


def test_title_matches_file_false_for_unrelated():
    assert title_matches_file("Other Video", "intro lesson") is False


def test_package_exports_version():
    from youtube_downloader import __version__
    assert isinstance(__version__, str)
    assert len(__version__.split(".")) == 3