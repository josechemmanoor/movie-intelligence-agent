from pathlib import Path
from src.subtitle_parser import parse_srt, timestamp_to_seconds

def test_timestamp():
    assert timestamp_to_seconds("00:01:02,500") == 62.5

def test_parse_srt(tmp_path: Path):
    p = tmp_path / "Test Movie.srt"
    p.write_text(
        "1\n00:00:01,000 --> 00:00:03,000\nHello <i>there</i>!\n\n"
        "2\n00:00:04,000 --> 00:00:05,500\nHow are you?\n",
        encoding="utf-8",
    )
    entries = parse_srt(p)
    assert len(entries) == 2
    assert entries[0].text == "Hello there!"
    assert entries[0].movie_title == "Test Movie"
    assert entries[1].start_seconds == 4.0
