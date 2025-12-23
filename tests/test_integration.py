"""Integration tests for the M4B splitter package.

These tests require ffmpeg to be installed and create actual M4B files.
"""

import pytest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m4b_splitter import (
    split_m4b,
    M4BSplitter,
    extract_chapters,
    extract_metadata,
    validate_m4b_file,
    check_dependencies,
    IPOD_PRESETS,
)
from m4b_splitter.probe import probe_file
from tests.test_utils import create_test_m4b


def ffmpeg_available() -> bool:
    """Check if ffmpeg is available for integration tests."""
    result = check_dependencies()
    return result.all_found


# Skip all tests in this module if ffmpeg is not available
pytestmark = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not available")


class TestProbeIntegration:
    """Integration tests for probing M4B files."""

    @pytest.fixture
    def test_m4b(self, tmp_path):
        """Create a test M4B file."""
        m4b_path = tmp_path / "test.m4b"
        if create_test_m4b(m4b_path, num_chapters=5, chapter_duration=30.0):
            return m4b_path
        pytest.skip("Could not create test M4B file")

    def test_probe_file(self, test_m4b):
        """Test probing an M4B file returns valid data."""
        data = probe_file(test_m4b)

        assert "format" in data
        assert "streams" in data
        assert "chapters" in data
        assert len(data["chapters"]) == 5

    def test_extract_chapters(self, test_m4b):
        """Test extracting chapters from M4B file."""
        chapters = extract_chapters(test_m4b)

        assert len(chapters) == 5
        assert chapters[0].title == "Chapter 1"
        assert chapters[0].start_time == 0.0
        assert chapters[0].duration == 30.0

    def test_extract_metadata(self, test_m4b):
        """Test extracting metadata from M4B file."""
        meta = extract_metadata(test_m4b)

        assert meta.title == "Test Audiobook"
        assert meta.artist == "Test Author"
        assert meta.duration == pytest.approx(150.0, abs=1.0)  # 5 * 30s

    def test_validate_m4b(self, test_m4b):
        """Test M4B validation."""
        is_valid, msg = validate_m4b_file(test_m4b)

        assert is_valid
        assert "5 chapters" in msg

    def test_validate_nonexistent_file(self, tmp_path):
        """Test validation of nonexistent file."""
        fake_path = tmp_path / "nonexistent.m4b"
        is_valid, msg = validate_m4b_file(fake_path)

        assert not is_valid
        assert "not found" in msg.lower()


class TestSplitIntegration:
    """Integration tests for splitting M4B files."""

    @pytest.fixture
    def test_m4b(self, tmp_path):
        """Create a test M4B file with 4 chapters of 30s each."""
        m4b_path = tmp_path / "test.m4b"
        if create_test_m4b(m4b_path, num_chapters=4, chapter_duration=30.0):
            return m4b_path
        pytest.skip("Could not create test M4B file")

    def test_split_basic(self, test_m4b, tmp_path):
        """Test basic splitting functionality."""
        output_dir = tmp_path / "output"

        # 4 chapters of 30s each, max 65s = 2 parts with 2 chapters each
        result = split_m4b(test_m4b, output_dir, max_duration_hours=65 / 3600)

        assert result.success
        assert len(result.parts) == 2

        # Verify output files exist
        for path in result.output_files:
            assert path.exists()

    def test_split_preserves_metadata_all_parts(self, test_m4b, tmp_path):
        """Test that metadata is preserved in ALL output files."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b, output_dir, max_duration_hours=65 / 3600  # Creates 2 parts
        )

        assert result.success
        assert len(result.parts) == 2

        # Check BOTH output files have correct metadata
        for i, output_file in enumerate(result.output_files, 1):
            meta = extract_metadata(output_file)

            # Title should include part number
            assert f"Part {i}/2" in meta.title, f"Part {i} missing part number in title"

            # Artist should be preserved
            assert meta.artist == "Test Author", f"Part {i} artist not preserved"

    def test_split_preserves_chapters_all_parts(self, test_m4b, tmp_path):
        """Test that chapters are preserved in ALL output files."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b, output_dir, max_duration_hours=65 / 3600  # Creates 2 parts
        )

        assert result.success
        assert len(result.parts) == 2

        # Check chapters in EACH output file
        for i, output_file in enumerate(result.output_files, 1):
            chapters = extract_chapters(output_file)

            # Each part should have 2 chapters
            assert (
                len(chapters) == 2
            ), f"Part {i} should have 2 chapters, got {len(chapters)}"

            # First chapter in each part should start at 0
            assert (
                chapters[0].start_time == 0.0
            ), f"Part {i} first chapter doesn't start at 0"

            # Verify chapter titles are correct
            if i == 1:
                assert chapters[0].title == "Chapter 1"
                assert chapters[1].title == "Chapter 2"
            else:
                assert chapters[0].title == "Chapter 3"
                assert chapters[1].title == "Chapter 4"

    def test_split_no_split_needed(self, test_m4b, tmp_path):
        """Test when file is already under max duration."""
        output_dir = tmp_path / "output"

        # File is 2 minutes, set max to 1 hour
        result = split_m4b(test_m4b, output_dir, max_duration_hours=1.0)

        assert result.success
        assert len(result.parts) == 1  # No split needed
        assert "No split needed" in result.error_message

    def test_split_custom_pattern(self, test_m4b, tmp_path):
        """Test splitting with custom filename pattern."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b,
            output_dir,
            max_duration_hours=65 / 3600,
            output_pattern="{artist} - {title} Part {part}.m4b",
        )

        assert result.success

        # Check filename format
        first_file = result.output_files[0]
        assert "Test Author" in first_file.name
        assert "Test Audiobook" in first_file.name
        assert "Part 1" in first_file.name


class TestIPodModeIntegration:
    """Integration tests for iPod mode."""

    @pytest.fixture
    def test_m4b(self, tmp_path):
        """Create a test M4B file."""
        m4b_path = tmp_path / "test.m4b"
        if create_test_m4b(m4b_path, num_chapters=2, chapter_duration=30.0):
            return m4b_path
        pytest.skip("Could not create test M4B file")

    def test_ipod_mode_standard_preset(self, test_m4b, tmp_path):
        """Test that iPod standard mode re-encodes audio correctly."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b,
            output_dir,
            max_duration_hours=45 / 3600,
            ipod_mode=True,
            ipod_preset="standard",
        )

        assert result.success

        # Check output file properties
        first_output = result.output_files[0]
        data = probe_file(first_output)

        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        assert audio_stream is not None
        # Should be mono at 22050Hz for standard preset
        assert audio_stream.get("channels") == 1
        assert audio_stream.get("sample_rate") == "22050"

    def test_ipod_mode_high_preset(self, test_m4b, tmp_path):
        """Test iPod mode with high quality preset."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b,
            output_dir,
            max_duration_hours=45 / 3600,
            ipod_mode=True,
            ipod_preset="high",
        )

        assert result.success

        first_output = result.output_files[0]
        data = probe_file(first_output)

        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        assert audio_stream is not None
        # Should be stereo at 44100Hz for high preset
        assert audio_stream.get("channels") == 2
        assert audio_stream.get("sample_rate") == "44100"

    def test_ipod_mode_video_preset(self, test_m4b, tmp_path):
        """Test iPod Video (5th Gen) preset."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b,
            output_dir,
            max_duration_hours=45 / 3600,
            ipod_mode=True,
            ipod_preset="video",
        )

        assert result.success

        first_output = result.output_files[0]
        data = probe_file(first_output)

        audio_stream = None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                audio_stream = stream
                break

        assert audio_stream is not None
        # Should be mono at 44100Hz for video preset
        assert audio_stream.get("channels") == 1
        assert audio_stream.get("sample_rate") == "44100"

    def test_ipod_mode_preserves_metadata(self, test_m4b, tmp_path):
        """Test that iPod mode preserves metadata in all parts."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b,
            output_dir,
            max_duration_hours=45 / 3600,
            ipod_mode=True,
            ipod_preset="standard",
        )

        assert result.success

        # Check metadata in all output files
        for i, output_file in enumerate(result.output_files, 1):
            meta = extract_metadata(output_file)
            assert meta.artist == "Test Author", f"Part {i} artist not preserved"
            assert f"Part {i}" in meta.title, f"Part {i} title incorrect"

    def test_ipod_mode_preserves_chapters(self, test_m4b, tmp_path):
        """Test that iPod mode preserves chapters in all parts."""
        output_dir = tmp_path / "output"

        result = split_m4b(
            test_m4b,
            output_dir,
            max_duration_hours=45 / 3600,
            ipod_mode=True,
            ipod_preset="standard",
        )

        assert result.success

        # Check chapters in all output files
        for i, output_file in enumerate(result.output_files, 1):
            chapters = extract_chapters(output_file)
            assert len(chapters) >= 1, f"Part {i} has no chapters"
            assert chapters[0].start_time == 0.0, f"Part {i} chapters don't start at 0"


class TestSplitterClass:
    """Integration tests for the M4BSplitter class."""

    @pytest.fixture
    def test_m4b(self, tmp_path):
        """Create a test M4B file."""
        m4b_path = tmp_path / "test.m4b"
        if create_test_m4b(m4b_path, num_chapters=4, chapter_duration=30.0):
            return m4b_path
        pytest.skip("Could not create test M4B file")

    def test_splitter_basic(self, test_m4b, tmp_path):
        """Test splitter class directly."""
        output_dir = tmp_path / "output"

        splitter = M4BSplitter()
        result = splitter.split(test_m4b, output_dir, max_duration_hours=65 / 3600)

        assert result.success
        assert len(result.parts) == 2

    def test_splitter_with_progress_callback(self, test_m4b, tmp_path):
        """Test that progress callback is called."""
        output_dir = tmp_path / "output"
        progress_calls = []

        def callback(step, percent, ffmpeg_prog):
            progress_calls.append((step, percent))

        splitter = M4BSplitter()
        result = splitter.split(
            test_m4b,
            output_dir,
            max_duration_hours=65 / 3600,
            progress_callback=callback,
        )

        assert result.success
        assert len(progress_calls) > 0

        # Should have various progress steps
        steps = [call[0] for call in progress_calls]
        assert any("Validating" in s for s in steps)
        assert any("metadata" in s.lower() for s in steps)


class TestEdgeCases:
    """Integration tests for edge cases."""

    def test_single_chapter_file(self, tmp_path):
        """Test splitting a file with only one chapter."""
        m4b_path = tmp_path / "single.m4b"
        if not create_test_m4b(m4b_path, num_chapters=1, chapter_duration=120.0):
            pytest.skip("Could not create test M4B file")

        output_dir = tmp_path / "output"

        # Even with 60s max, can't split a single 120s chapter
        result = split_m4b(m4b_path, output_dir, max_duration_hours=60 / 3600)

        assert result.success
        # Should still create one file with the single chapter
        assert len(result.parts) == 1

    def test_many_small_chapters(self, tmp_path):
        """Test splitting a file with many small chapters."""
        m4b_path = tmp_path / "many_chapters.m4b"
        # 10 chapters of 10 seconds each
        if not create_test_m4b(m4b_path, num_chapters=10, chapter_duration=10.0):
            pytest.skip("Could not create test M4B file")

        output_dir = tmp_path / "output"

        # 25 second parts should fit 2 chapters each
        result = split_m4b(m4b_path, output_dir, max_duration_hours=25 / 3600)

        assert result.success
        # Should have 5 parts with 2 chapters each
        assert len(result.parts) == 5

        for part in result.parts:
            assert len(part.chapters) == 2
