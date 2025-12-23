"""Shared pytest fixtures and configuration."""

import sys
from pathlib import Path

import pytest

# Ensure the package is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def tmp_m4b_dir(tmp_path):
    """Create a temporary directory for M4B test files."""
    m4b_dir = tmp_path / "m4b_files"
    m4b_dir.mkdir()
    return m4b_dir


@pytest.fixture
def sample_chapters():
    """Create sample chapters for testing."""
    from m4b_splitter.models import Chapter

    return [
        Chapter(id=0, title="Introduction", start_time=0.0, end_time=60.0),
        Chapter(id=1, title="Chapter 1", start_time=60.0, end_time=180.0),
        Chapter(id=2, title="Chapter 2", start_time=180.0, end_time=300.0),
        Chapter(id=3, title="Chapter 3", start_time=300.0, end_time=420.0),
        Chapter(id=4, title="Conclusion", start_time=420.0, end_time=480.0),
    ]


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    from m4b_splitter.models import AudioMetadata

    return AudioMetadata(
        title="Sample Audiobook",
        artist="Test Author",
        album="Test Series",
        album_artist="Test Author",
        genre="Audiobook",
        date="2024",
        duration=480.0,
        bit_rate=128000,
        sample_rate=44100,
        channels=2,
        codec="aac",
    )
