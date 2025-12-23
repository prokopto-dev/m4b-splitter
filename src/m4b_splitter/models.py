"""Data models for M4B splitter."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Chapter:
    """Represents a chapter in an M4B audiobook."""

    id: int
    title: str
    start_time: float  # seconds
    end_time: float    # seconds

    @property
    def duration(self) -> float:
        """Get chapter duration in seconds."""
        return self.end_time - self.start_time

    def __str__(self) -> str:
        return f"Chapter {self.id}: {self.title} ({self.duration:.1f}s)"


@dataclass
class AudioMetadata:
    """Metadata for an M4B audiobook file."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    album_artist: str | None = None
    composer: str | None = None
    genre: str | None = None
    date: str | None = None
    comment: str | None = None
    encoder: str | None = None
    duration: float = 0.0  # Total duration in seconds
    bit_rate: int = 0
    sample_rate: int = 0
    channels: int = 0
    codec: str | None = None
    extra_tags: dict[str, str] = field(default_factory=dict)

    def to_ffmpeg_metadata(self) -> dict[str, str]:
        """Convert to ffmpeg metadata format."""
        metadata = {}
        if self.title:
            metadata["title"] = self.title
        if self.artist:
            metadata["artist"] = self.artist
        if self.album:
            metadata["album"] = self.album
        if self.album_artist:
            metadata["album_artist"] = self.album_artist
        if self.composer:
            metadata["composer"] = self.composer
        if self.genre:
            metadata["genre"] = self.genre
        if self.date:
            metadata["date"] = self.date
        if self.comment:
            metadata["comment"] = self.comment
        metadata.update(self.extra_tags)
        return metadata


@dataclass
class SplitPart:
    """Represents a part of a split audiobook."""

    part_number: int
    total_parts: int
    chapters: list[Chapter]
    output_path: Path

    @property
    def start_time(self) -> float:
        """Get start time of this part."""
        return self.chapters[0].start_time if self.chapters else 0.0

    @property
    def end_time(self) -> float:
        """Get end time of this part."""
        return self.chapters[-1].end_time if self.chapters else 0.0

    @property
    def duration(self) -> float:
        """Get total duration of this part."""
        return self.end_time - self.start_time

    @property
    def chapter_titles(self) -> list[str]:
        """Get list of chapter titles in this part."""
        return [ch.title for ch in self.chapters]

    def __str__(self) -> str:
        return f"Part {self.part_number}/{self.total_parts}: {len(self.chapters)} chapters, {self.duration:.1f}s"


@dataclass
class SplitResult:
    """Result of an M4B split operation."""

    source_file: Path
    parts: list[SplitPart]
    original_metadata: AudioMetadata
    success: bool = True
    error_message: str | None = None

    @property
    def output_files(self) -> list[Path]:
        """Get list of output file paths."""
        return [part.output_path for part in self.parts]

    def __str__(self) -> str:
        if self.success:
            return f"Split '{self.source_file.name}' into {len(self.parts)} parts"
        return f"Failed to split '{self.source_file.name}': {self.error_message}"
