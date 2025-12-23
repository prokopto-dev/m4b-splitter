"""
M4B Splitter - Split M4B audiobook files by chapters.

This package provides functionality to split large M4B audiobook files
into smaller parts at chapter boundaries, while preserving metadata
and chapter information.

Basic usage:
    >>> from m4b_splitter import split_m4b
    >>> result = split_m4b("audiobook.m4b", "./output", max_duration_hours=4)
    >>> print(result.output_files)

For iPod Classic compatibility:
    >>> result = split_m4b("audiobook.m4b", "./output", ipod_mode=True)

For more control, use the M4BSplitter class:
    >>> from m4b_splitter import M4BSplitter, ConsoleProgress
    >>> splitter = M4BSplitter(progress_callback=ConsoleProgress())
    >>> result = splitter.split("audiobook.m4b", "./output")

To check if ffmpeg is installed:
    >>> from m4b_splitter import check_dependencies
    >>> result = check_dependencies()
    >>> if not result.all_found:
    ...     print("Please install ffmpeg")

Requirements:
    - Python 3.12+
    - ffmpeg and ffprobe installed and in PATH
"""

__version__ = "1.2.0"
__author__ = "M4B Splitter Contributors"

from m4b_splitter.dependencies import (
    DependencyCheckResult,
    DependencyStatus,
    OSType,
    check_dependencies,
    ensure_dependencies,
    format_dependency_check,
    require_dependencies,
)
from m4b_splitter.models import AudioMetadata, Chapter, SplitPart, SplitResult
from m4b_splitter.probe import (
    ProbeError,
    extract_chapters,
    extract_metadata,
    get_duration,
    probe_file,
    validate_m4b_file,
)
from m4b_splitter.progress import (
    ConsoleProgress,
    ProgressCallback,
    ProgressStep,
    ProgressTracker,
    ProgressUpdate,
    SilentProgress,
)
from m4b_splitter.splitter import (
    IPOD_PRESETS,
    FFmpegProgress,
    IPodSettings,
    M4BSplitter,
    SplitterError,
    format_time_human,
    split_m4b,
)

__all__ = [
    "IPOD_PRESETS",
    "AudioMetadata",
    # Models
    "Chapter",
    "ConsoleProgress",
    "DependencyCheckResult",
    "DependencyStatus",
    "FFmpegProgress",
    # iPod settings
    "IPodSettings",
    # Splitter
    "M4BSplitter",
    "OSType",
    "ProbeError",
    "ProgressCallback",
    # Progress tracking
    "ProgressStep",
    "ProgressTracker",
    "ProgressUpdate",
    "SilentProgress",
    "SplitPart",
    "SplitResult",
    "SplitterError",
    # Version
    "__version__",
    # Dependency checking
    "check_dependencies",
    "ensure_dependencies",
    "extract_chapters",
    "extract_metadata",
    "format_dependency_check",
    "format_time_human",
    "get_duration",
    # Probe functions
    "probe_file",
    "require_dependencies",
    "split_m4b",
    "validate_m4b_file",
]
