from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import re

TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{3})"
)

@dataclass
class SubtitleEntry:
    index: int
    start: str
    end: str
    start_seconds: float
    end_seconds: float
    text: str
    movie_title: str
    source_file: str

    def to_dict(self):
        return asdict(self)

def timestamp_to_seconds(ts: str) -> float:
    ts = ts.replace(",", ".")
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)

def seconds_to_timestamp(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    sec = seconds % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}"

def clean_dialogue(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\{[^}]+\}", " ", text)
    text = text.replace("\\N", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def parse_srt(path: str | Path, movie_title: str | None = None) -> list[SubtitleEntry]:
    path = Path(path)
    title = movie_title or path.stem.replace("_", " ").replace(".", " ").strip()
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    blocks = re.split(r"\n\s*\n", raw)
    entries = []

    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        match_line_index = None
        match = None
        for i, line in enumerate(lines[:3]):
            m = TIMESTAMP_RE.search(line)
            if m:
                match_line_index = i
                match = m
                break

        if not match:
            continue

        try:
            idx = int(lines[0]) if lines[0].isdigit() else len(entries) + 1
        except ValueError:
            idx = len(entries) + 1

        dialogue = clean_dialogue(" ".join(lines[match_line_index + 1:]))
        if not dialogue:
            continue

        start = match.group("start")
        end = match.group("end")

        entries.append(
            SubtitleEntry(
                index=idx,
                start=start,
                end=end,
                start_seconds=timestamp_to_seconds(start),
                end_seconds=timestamp_to_seconds(end),
                text=dialogue,
                movie_title=title,
                source_file=str(path),
            )
        )

    return entries

def chunk_entries(entries: list[SubtitleEntry], window_size: int = 8, overlap: int = 2):
    if not entries:
        return []

    step = max(1, window_size - overlap)
    chunks = []

    for start_i in range(0, len(entries), step):
        group = entries[start_i:start_i + window_size]
        if not group:
            break

        text = " ".join(e.text for e in group)
        first, last = group[0], group[-1]

        chunks.append({
            "text": text,
            "movie_title": first.movie_title,
            "start": first.start,
            "end": last.end,
            "start_seconds": first.start_seconds,
            "end_seconds": last.end_seconds,
            "source_file": first.source_file,
            "subtitle_start_index": first.index,
            "subtitle_end_index": last.index,
        })

        if start_i + window_size >= len(entries):
            break

    return chunks
