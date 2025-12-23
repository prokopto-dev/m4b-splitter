"""Core M4B splitting functionality."""

import re
import subprocess
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from m4b_splitter.models import AudioMetadata, Chapter, SplitPart, SplitResult
from m4b_splitter.probe import extract_chapters, extract_metadata, validate_m4b_file


class SplitterError(Exception):
    """Exception raised when splitting fails."""

    pass


class IPodPreset(str, Enum):
    """Available iPod encoding presets."""

    STANDARD = "standard"
    HIGH = "high"
    EXTENDED = "extended"
    VIDEO = "video"  # iPod Video (5th Gen) compatibility


@dataclass
class IPodSettings:
    """
    Audio settings optimized for iPod devices.

    The iPod Classic has limitations:
    - 32-bit sample counter limits playback to ~27-37 hours at standard sample rates
    - AAC-LC codec is well supported
    - Lower sample rates extend maximum duration

    These settings provide good compatibility while maintaining reasonable quality.
    """

    # Sample rate in Hz
    sample_rate: int = 22050

    # Bitrate in kbps
    bitrate: int = 64

    # Audio channels (1=mono, 2=stereo)
    channels: int = 1

    # AAC encoder to use (aac is built-in, aac_at is macOS AudioToolbox)
    encoder: str = "aac"

    # Additional encoder options
    encoder_options: dict[str, str] = field(default_factory=dict)

    # Use CBR mode for better compatibility
    use_cbr: bool = False

    # Preset name for display
    preset_name: str = "custom"

    @classmethod
    def standard(cls) -> "IPodSettings":
        """Standard audiobook settings (good balance for iPod Classic)."""
        return cls(
            sample_rate=22050,
            bitrate=64,
            channels=1,
            encoder="aac",
            preset_name="standard",
        )

    @classmethod
    def high_quality(cls) -> "IPodSettings":
        """Higher quality settings (shorter max duration)."""
        return cls(
            sample_rate=44100,
            bitrate=128,
            channels=2,
            encoder="aac",
            preset_name="high",
        )

    @classmethod
    def extended_duration(cls) -> "IPodSettings":
        """Extended duration settings (lower quality, longer playback)."""
        return cls(
            sample_rate=16000,
            bitrate=48,
            channels=1,
            encoder="aac",
            preset_name="extended",
        )

    @classmethod
    def ipod_video(cls) -> "IPodSettings":
        """
        iPod Video (5th Gen) compatible settings.

        Uses CBR 80kbps mono at 44.1kHz for maximum compatibility
        with older iPod Video devices.
        """
        return cls(
            sample_rate=44100,
            bitrate=80,
            channels=1,
            encoder="aac",
            use_cbr=True,
            preset_name="video",
        )

    @property
    def max_duration_hours(self) -> float:
        """Approximate maximum duration in hours for iPod Classic."""
        # iPod Classic uses 32-bit sample counter
        max_samples = 2**32 - 1
        max_seconds = max_samples / self.sample_rate
        return max_seconds / 3600

    def get_ffmpeg_audio_args(self) -> list[str]:
        """Get ffmpeg arguments for audio encoding."""
        args = [
            "-c:a",
            self.encoder,
            "-ar",
            str(self.sample_rate),
            "-ac",
            str(self.channels),
            "-b:a",
            f"{self.bitrate}k",
        ]

        # Add CBR mode if requested (mainly for iPod Video compatibility)
        if self.use_cbr:
            # For standard aac encoder, use strict CBR
            args.extend(["-profile:a", "aac_low"])

        # Add any additional encoder options
        for key, value in self.encoder_options.items():
            args.extend([f"-{key}", value])

        return args

    def __str__(self) -> str:
        mode = "CBR" if self.use_cbr else "VBR"
        return (
            f"{self.preset_name}: {self.sample_rate}Hz, {self.bitrate}kbps {mode}, "
            f"{'mono' if self.channels == 1 else 'stereo'} "
            f"(max ~{self.max_duration_hours:.0f}h)"
        )


# Preset iPod settings lookup
IPOD_PRESETS: dict[str, IPodSettings] = {
    "standard": IPodSettings.standard(),
    "high": IPodSettings.high_quality(),
    "extended": IPodSettings.extended_duration(),
    "video": IPodSettings.ipod_video(),
}


@dataclass
class FFmpegProgress:
    """Progress information from ffmpeg."""

    frame: int = 0
    fps: float = 0.0
    size_kb: int = 0
    time_seconds: float = 0.0
    bitrate_kbps: float = 0.0
    speed: float = 0.0
    percent: float = 0.0


def parse_ffmpeg_progress(line: str, total_duration: float) -> FFmpegProgress | None:
    """
    Parse ffmpeg progress output line.

    Args:
        line: A line from ffmpeg stderr output.
        total_duration: Total duration in seconds for percentage calculation.

    Returns:
        FFmpegProgress object or None if line doesn't contain progress info.
    """
    if "time=" not in line:
        return None

    progress = FFmpegProgress()

    # Parse time (format: HH:MM:SS.ss or N/A)
    time_match = re.search(r"time=(\d+):(\d+):(\d+\.?\d*)", line)
    if time_match:
        hours, mins, secs = time_match.groups()
        progress.time_seconds = int(hours) * 3600 + int(mins) * 60 + float(secs)
        if total_duration > 0:
            progress.percent = min(100.0, (progress.time_seconds / total_duration) * 100)

    # Parse size
    size_match = re.search(r"size=\s*(\d+)kB", line)
    if size_match:
        progress.size_kb = int(size_match.group(1))

    # Parse bitrate
    bitrate_match = re.search(r"bitrate=\s*([\d.]+)kbits/s", line)
    if bitrate_match:
        progress.bitrate_kbps = float(bitrate_match.group(1))

    # Parse speed
    speed_match = re.search(r"speed=\s*([\d.]+)x", line)
    if speed_match:
        progress.speed = float(speed_match.group(1))

    return progress


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm for ffmpeg."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def format_time_human(seconds: float) -> str:
    """Format seconds as human readable string."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use in filenames."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized or "untitled"


def plan_splits(chapters: list[Chapter], max_duration_seconds: float) -> list[list[Chapter]]:
    """
    Plan how to split chapters into parts based on maximum duration.

    Splits only occur at chapter boundaries. If a single chapter exceeds
    the maximum duration, it will be placed in its own part.

    Args:
        chapters: List of chapters to split.
        max_duration_seconds: Maximum duration per part in seconds.

    Returns:
        List of lists, where each inner list contains chapters for one part.
    """
    if not chapters:
        return []

    parts: list[list[Chapter]] = []
    current_part: list[Chapter] = []
    current_duration = 0.0

    for chapter in chapters:
        chapter_duration = chapter.duration

        # If adding this chapter would exceed the limit
        if current_duration + chapter_duration > max_duration_seconds and current_part:
            # Save current part and start a new one
            parts.append(current_part)
            current_part = [chapter]
            current_duration = chapter_duration
        else:
            # Add chapter to current part
            current_part.append(chapter)
            current_duration += chapter_duration

    # Don't forget the last part
    if current_part:
        parts.append(current_part)

    return parts


def extract_cover_art(input_file: Path, output_file: Path) -> bool:
    """
    Extract cover art from an M4B file.

    Args:
        input_file: Path to the M4B file.
        output_file: Path to save the cover art.

    Returns:
        True if cover art was extracted, False otherwise.
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-an",  # No audio
        "-vcodec",
        "copy",
        str(output_file),
    ]

    try:
        result = subprocess.run(cmd, check=False, capture_output=True, text=True)
        return result.returncode == 0 and output_file.exists() and output_file.stat().st_size > 0
    except Exception:
        return False


def create_metadata_file(
    metadata: AudioMetadata,
    chapters: list[Chapter],
    part_number: int,
    total_parts: int,
    temp_dir: Path,
) -> Path:
    """
    Create an ffmpeg metadata file for a split part.

    Args:
        metadata: Original audio metadata.
        chapters: Chapters in this part.
        part_number: Current part number.
        total_parts: Total number of parts.
        temp_dir: Temporary directory for the metadata file.

    Returns:
        Path to the created metadata file.
    """
    metadata_path = temp_dir / f"metadata_part{part_number}.txt"

    # Calculate time offset (chapters in this part start at their original times)
    time_offset = chapters[0].start_time if chapters else 0

    with open(metadata_path, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")

        # Write global metadata
        title = metadata.title or "Audiobook"
        f.write(f"title={title} - Part {part_number}/{total_parts}\n")

        if metadata.artist:
            f.write(f"artist={metadata.artist}\n")
        if metadata.album:
            f.write(f"album={metadata.album}\n")
        if metadata.album_artist:
            f.write(f"album_artist={metadata.album_artist}\n")
        if metadata.composer:
            f.write(f"composer={metadata.composer}\n")
        if metadata.genre:
            f.write(f"genre={metadata.genre}\n")
        if metadata.date:
            f.write(f"date={metadata.date}\n")
        if metadata.comment:
            comment = metadata.comment.replace("\n", " ")
            f.write(f"comment={comment}\n")

        # Track numbering
        f.write(f"track={part_number}/{total_parts}\n")

        # Write extra tags
        for key, value in metadata.extra_tags.items():
            # Escape special characters
            value = (
                value.replace("=", "\\=").replace(";", "\\;").replace("#", "\\#").replace("\n", " ")
            )
            f.write(f"{key}={value}\n")

        # Write chapter information
        for chapter in chapters:
            # Adjust times relative to part start
            start_ms = int((chapter.start_time - time_offset) * 1000)
            end_ms = int((chapter.end_time - time_offset) * 1000)

            f.write("\n[CHAPTER]\n")
            f.write("TIMEBASE=1/1000\n")
            f.write(f"START={start_ms}\n")
            f.write(f"END={end_ms}\n")
            # Escape chapter title
            ch_title = chapter.title.replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")
            f.write(f"title={ch_title}\n")

    return metadata_path


def run_ffmpeg_with_progress(
    cmd: list[str],
    total_duration: float,
    progress_callback: Callable[[FFmpegProgress], None] | None = None,
) -> tuple[bool, str]:
    """
    Run ffmpeg command with progress tracking.

    Args:
        cmd: FFmpeg command as list of arguments.
        total_duration: Total duration in seconds for progress calculation.
        progress_callback: Optional callback for progress updates.

    Returns:
        Tuple of (success, error_message).
    """
    # Add progress flag to ffmpeg command
    cmd_with_progress = cmd.copy()
    # Insert -progress pipe:1 after ffmpeg
    if "ffmpeg" in cmd_with_progress[0]:
        cmd_with_progress.insert(1, "-progress")
        cmd_with_progress.insert(2, "pipe:1")
        cmd_with_progress.insert(3, "-stats_period")
        cmd_with_progress.insert(4, "0.5")

    try:
        process = subprocess.Popen(
            cmd_with_progress,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        stderr_lines: list[str] = []

        def read_stderr():
            if process.stderr:
                for line in process.stderr:
                    stderr_lines.append(line)
                    if progress_callback:
                        progress = parse_ffmpeg_progress(line, total_duration)
                        if progress:
                            progress_callback(progress)

        # Read stderr in a separate thread
        stderr_thread = threading.Thread(target=read_stderr)
        stderr_thread.start()

        # Also read stdout for progress info
        if process.stdout:
            for line in process.stdout:
                if progress_callback and "out_time_ms=" in line:
                    try:
                        time_ms = int(line.split("=")[1].strip())
                        progress = FFmpegProgress()
                        progress.time_seconds = time_ms / 1_000_000
                        if total_duration > 0:
                            progress.percent = min(
                                100.0, (progress.time_seconds / total_duration) * 100
                            )
                        progress_callback(progress)
                    except (ValueError, IndexError):
                        pass

        process.wait()
        stderr_thread.join(timeout=5)

        if process.returncode != 0:
            return False, "".join(stderr_lines)

        return True, ""

    except Exception as e:
        return False, str(e)


def split_audio_segment(
    input_file: Path,
    output_file: Path,
    start_time: float,
    end_time: float,
    metadata_file: Path,
    cover_file: Path | None = None,
    ipod_settings: IPodSettings | None = None,
    progress_callback: Callable[[FFmpegProgress], None] | None = None,
) -> tuple[bool, str]:
    """
    Split a segment from an M4B file.

    Args:
        input_file: Source M4B file.
        output_file: Output file path.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        metadata_file: Metadata file to apply (required).
        cover_file: Optional cover art file.
        ipod_settings: Optional iPod-compatible encoding settings.
        progress_callback: Optional callback for progress updates.

    Returns:
        Tuple of (success, error_message).
    """
    duration = end_time - start_time

    # Build ffmpeg command
    # Key fix: We need to properly handle metadata and chapters for EVERY part
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        format_time(start_time),
        "-i",
        str(input_file),
        "-i",
        str(metadata_file),
    ]

    # Add cover art input if available
    cover_input_idx = 2
    if cover_file and cover_file.exists():
        cmd.extend(["-i", str(cover_file)])
        cover_input_idx = 2

    # Duration
    cmd.extend(["-t", format_time(duration)])

    # Audio encoding settings
    if ipod_settings:
        # Re-encode for iPod compatibility
        cmd.extend(ipod_settings.get_ffmpeg_audio_args())
    else:
        # Copy audio stream without re-encoding (fast, lossless)
        cmd.extend(["-c:a", "copy"])

    # Map audio from input file
    cmd.extend(["-map", "0:a:0"])

    # Map cover art if available
    if cover_file and cover_file.exists():
        cmd.extend(
            [
                "-map",
                f"{cover_input_idx}:v:0",
                "-c:v",
                "copy",
                "-disposition:v:0",
                "attached_pic",
            ]
        )

    # Apply metadata from metadata file
    # This is the key fix: map_metadata and map_chapters from the metadata file (input 1)
    cmd.extend(
        [
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
        ]
    )

    # Ensure faststart for better streaming/seeking
    cmd.extend(["-movflags", "+faststart"])

    # Output format
    cmd.extend(["-f", "ipod", str(output_file)])

    return run_ffmpeg_with_progress(cmd, duration, progress_callback)


class M4BSplitter:
    """
    Main class for splitting M4B audiobook files.

    This class provides functionality to split large M4B audiobook files
    into smaller parts at chapter boundaries, while preserving metadata
    and chapter information.
    """

    def __init__(self) -> None:
        """Initialize the M4B splitter."""
        pass

    def split(
        self,
        input_file: Path | str,
        output_dir: Path | str,
        max_duration_hours: float = 8.0,
        output_pattern: str = "{title} - Part {part} of {total}.m4b",
        ipod_mode: bool = False,
        ipod_preset: str = "standard",
        progress_callback: (Callable[[str, float, FFmpegProgress | None], None] | None) = None,
    ) -> SplitResult:
        """
        Split an M4B file into parts based on maximum duration.

        Args:
            input_file: Path to the input M4B file.
            output_dir: Directory for output files.
            max_duration_hours: Maximum duration per part in hours.
            output_pattern: Filename pattern for output files.
                Available placeholders: {title}, {part}, {total}, {artist}
            ipod_mode: If True, re-encode audio for iPod compatibility.
            ipod_preset: iPod encoding preset ('standard', 'high', 'extended', 'video').
            progress_callback: Optional callback(step_name, overall_percent, ffmpeg_progress)

        Returns:
            SplitResult containing information about the split.
        """
        input_file = Path(input_file)
        output_dir = Path(output_dir)
        max_duration_seconds = max_duration_hours * 3600

        def report_progress(
            step: str, percent: float, ffmpeg_prog: FFmpegProgress | None = None
        ) -> SplitResult:
            if progress_callback:
                progress_callback(step, percent, ffmpeg_prog)

        # Get iPod settings if enabled
        ipod_settings: IPodSettings | None = None
        if ipod_mode:
            ipod_settings = IPOD_PRESETS.get(ipod_preset, IPodSettings.standard())

        try:
            # Step 1: Validate input file
            report_progress("Validating input file", 0)

            is_valid, msg = validate_m4b_file(input_file)
            if not is_valid:
                raise SplitterError(f"Invalid input file: {msg}")

            # Step 2: Extract metadata
            report_progress("Extracting metadata", 5)
            metadata = extract_metadata(input_file)

            # Step 3: Extract chapters
            report_progress("Extracting chapters", 10)
            chapters = extract_chapters(input_file)

            # Step 4: Plan splits
            report_progress("Planning splits", 15)
            split_plan = plan_splits(chapters, max_duration_seconds)
            total_parts = len(split_plan)

            if total_parts == 1 and not ipod_mode:
                return SplitResult(
                    source_file=input_file,
                    parts=[
                        SplitPart(
                            part_number=1,
                            total_parts=1,
                            chapters=chapters,
                            output_path=input_file,
                        )
                    ],
                    original_metadata=metadata,
                    success=True,
                    error_message="No split needed - file already under maximum duration",
                )

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Create temporary directory for intermediate files
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Step 5: Extract cover art (once, reuse for all parts)
                report_progress("Extracting cover art", 18)
                cover_file = temp_path / "cover.jpg"
                has_cover = extract_cover_art(input_file, cover_file)
                if not has_cover:
                    cover_file = None

                # Step 6: Split audio - this is the main work
                parts: list[SplitPart] = []
                base_progress = 20
                progress_per_part = 75 / total_parts  # Reserve 20-95% for splitting

                for part_num, part_chapters in enumerate(split_plan, 1):
                    part_base_progress = base_progress + (part_num - 1) * progress_per_part

                    # Generate output filename
                    title = sanitize_filename(metadata.title or input_file.stem)
                    artist = sanitize_filename(metadata.artist or "Unknown")

                    filename = output_pattern.format(
                        title=title, part=part_num, total=total_parts, artist=artist
                    )
                    # Sanitize the final filename
                    filename = sanitize_filename(filename)
                    if not filename.endswith(".m4b"):
                        filename += ".m4b"

                    output_file = output_dir / filename

                    # Create metadata file for this part
                    # This is created fresh for EACH part with correct chapters
                    metadata_file = create_metadata_file(
                        metadata=metadata,
                        chapters=part_chapters,
                        part_number=part_num,
                        total_parts=total_parts,
                        temp_dir=temp_path,
                    )

                    # Extract this part
                    start_time = part_chapters[0].start_time
                    end_time = part_chapters[-1].end_time

                    def ffmpeg_progress_handler(prog: FFmpegProgress) -> None:
                        # Convert ffmpeg progress to overall progress
                        part_progress = prog.percent / 100 * progress_per_part
                        overall = part_base_progress + part_progress
                        report_progress(f"Encoding part {part_num}/{total_parts}", overall, prog)

                    report_progress(f"Processing part {part_num}/{total_parts}", part_base_progress)

                    success, error = split_audio_segment(
                        input_file=input_file,
                        output_file=output_file,
                        start_time=start_time,
                        end_time=end_time,
                        metadata_file=metadata_file,
                        cover_file=cover_file,
                        ipod_settings=ipod_settings,
                        progress_callback=ffmpeg_progress_handler,
                    )

                    if not success:
                        raise SplitterError(f"Failed to create part {part_num}: {error}")

                    if not output_file.exists():
                        raise SplitterError(f"Output file was not created: {output_file}")

                    parts.append(
                        SplitPart(
                            part_number=part_num,
                            total_parts=total_parts,
                            chapters=part_chapters,
                            output_path=output_file,
                        )
                    )

                report_progress("Finalizing", 98)

            report_progress("Complete", 100)

            return SplitResult(
                source_file=input_file,
                parts=parts,
                original_metadata=metadata,
                success=True,
            )

        except SplitterError as e:
            return SplitResult(
                source_file=input_file,
                parts=[],
                original_metadata=AudioMetadata(),
                success=False,
                error_message=str(e),
            )
        except Exception as e:
            return SplitResult(
                source_file=input_file,
                parts=[],
                original_metadata=AudioMetadata(),
                success=False,
                error_message=f"Unexpected error: {e}",
            )


def split_m4b(
    input_file: Path | str,
    output_dir: Path | str,
    max_duration_hours: float = 8.0,
    output_pattern: str = "{title} - Part {part} of {total}.m4b",
    ipod_mode: bool = False,
    ipod_preset: str = "standard",
    progress_callback: (Callable[[str, float, FFmpegProgress | None], None] | None) = None,
) -> SplitResult:
    """
    Convenience function to split an M4B file.

    This is a simpler interface to the M4BSplitter class for basic usage.

    Args:
        input_file: Path to the input M4B file.
        output_dir: Directory for output files.
        max_duration_hours: Maximum duration per part in hours.
        output_pattern: Filename pattern for output files.
        ipod_mode: If True, re-encode audio for iPod compatibility.
        ipod_preset: iPod encoding preset:
            - 'standard': 22050Hz, 64kbps mono (max ~55h per file)
            - 'high': 44100Hz, 128kbps stereo (max ~27h per file)
            - 'extended': 16000Hz, 48kbps mono (max ~74h per file)
            - 'video': 44100Hz, 80kbps CBR mono (iPod Video 5th Gen compatible)
        progress_callback: Optional callback(step_name, overall_percent, ffmpeg_progress)

    Returns:
        SplitResult containing information about the split.
    """
    splitter = M4BSplitter()
    return splitter.split(
        input_file=input_file,
        output_dir=output_dir,
        max_duration_hours=max_duration_hours,
        output_pattern=output_pattern,
        ipod_mode=ipod_mode,
        ipod_preset=ipod_preset,
        progress_callback=progress_callback,
    )
