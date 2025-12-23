"""Module for probing M4B files to extract metadata and chapters."""

import json
import subprocess
from pathlib import Path

from m4b_splitter.models import AudioMetadata, Chapter


class ProbeError(Exception):
    """Exception raised when probing a file fails."""

    pass


def probe_file(file_path: Path) -> dict:
    """
    Probe an M4B file using ffprobe and return raw JSON data.

    Args:
        file_path: Path to the M4B file.

    Returns:
        Dictionary containing ffprobe output.

    Raises:
        ProbeError: If ffprobe fails or file doesn't exist.
    """
    if not file_path.exists():
        raise ProbeError(f"File not found: {file_path}")

    cmd = [
        "ffprobe",
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        str(file_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        raise ProbeError(f"ffprobe failed: {e.stderr}") from e
    except json.JSONDecodeError as e:
        raise ProbeError(f"Failed to parse ffprobe output: {e}") from e


def extract_chapters(file_path: Path) -> list[Chapter]:
    """
    Extract chapter information from an M4B file.

    Args:
        file_path: Path to the M4B file.

    Returns:
        List of Chapter objects.

    Raises:
        ProbeError: If probing fails or no chapters found.
    """
    data = probe_file(file_path)

    chapters_data = data.get("chapters", [])
    if not chapters_data:
        raise ProbeError(f"No chapters found in: {file_path}")

    chapters = []
    for i, ch in enumerate(chapters_data):
        # Get chapter times - ffprobe provides these as strings
        start_time = float(ch.get("start_time", 0))
        end_time = float(ch.get("end_time", 0))

        # Get title from tags or use default
        tags = ch.get("tags", {})
        title = tags.get("title", f"Chapter {i + 1}")

        chapters.append(
            Chapter(id=i, title=title, start_time=start_time, end_time=end_time)
        )

    return chapters


def extract_metadata(file_path: Path) -> AudioMetadata:
    """
    Extract audio metadata from an M4B file.

    Args:
        file_path: Path to the M4B file.

    Returns:
        AudioMetadata object with extracted information.

    Raises:
        ProbeError: If probing fails.
    """
    data = probe_file(file_path)

    format_data = data.get("format", {})
    format_tags = format_data.get("tags", {})

    # Find audio stream
    streams = data.get("streams", [])
    audio_stream = None
    for stream in streams:
        if stream.get("codec_type") == "audio":
            audio_stream = stream
            break

    # Extract known tags (case-insensitive lookup)
    def get_tag(key: str) -> str | None:
        # Try exact match first
        if key in format_tags:
            return format_tags[key]
        # Try case-insensitive
        key_lower = key.lower()
        for k, v in format_tags.items():
            if k.lower() == key_lower:
                return v
        return None

    # Known tag keys to extract
    known_keys = {
        "title",
        "artist",
        "album",
        "album_artist",
        "composer",
        "genre",
        "date",
        "comment",
        "encoder",
    }

    # Build extra tags dict with remaining tags
    extra_tags = {}
    for k, v in format_tags.items():
        if k.lower() not in known_keys:
            extra_tags[k] = v

    metadata = AudioMetadata(
        title=get_tag("title"),
        artist=get_tag("artist"),
        album=get_tag("album"),
        album_artist=get_tag("album_artist"),
        composer=get_tag("composer"),
        genre=get_tag("genre"),
        date=get_tag("date"),
        comment=get_tag("comment"),
        encoder=get_tag("encoder"),
        duration=float(format_data.get("duration", 0)),
        bit_rate=int(format_data.get("bit_rate", 0)),
        extra_tags=extra_tags,
    )

    # Add stream-specific info if available
    if audio_stream:
        metadata.sample_rate = int(audio_stream.get("sample_rate", 0))
        metadata.channels = int(audio_stream.get("channels", 0))
        metadata.codec = audio_stream.get("codec_name")

    return metadata


def get_duration(file_path: Path) -> float:
    """
    Get the total duration of an M4B file in seconds.

    Args:
        file_path: Path to the M4B file.

    Returns:
        Duration in seconds.

    Raises:
        ProbeError: If probing fails.
    """
    data = probe_file(file_path)
    format_data = data.get("format", {})
    return float(format_data.get("duration", 0))


def validate_m4b_file(file_path: Path) -> tuple[bool, str]:
    """
    Validate that a file is a valid M4B audiobook.

    Args:
        file_path: Path to the file to validate.

    Returns:
        Tuple of (is_valid, message).
    """
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    if file_path.suffix.lower() not in (".m4b", ".m4a", ".mp4"):
        return False, f"Invalid file extension: {file_path.suffix}"

    try:
        data = probe_file(file_path)

        # Check for audio stream
        streams = data.get("streams", [])
        has_audio = any(s.get("codec_type") == "audio" for s in streams)
        if not has_audio:
            return False, "No audio stream found"

        # Check for chapters
        chapters = data.get("chapters", [])
        if not chapters:
            return False, "No chapters found (required for splitting)"

        return True, f"Valid M4B file with {len(chapters)} chapters"

    except ProbeError as e:
        return False, str(e)
