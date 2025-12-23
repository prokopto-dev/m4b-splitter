"""Unit tests for the models module."""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m4b_splitter.models import Chapter, AudioMetadata, SplitPart, SplitResult


class TestChapter:
    """Tests for the Chapter dataclass."""
    
    def test_chapter_creation(self):
        """Test basic chapter creation."""
        ch = Chapter(id=0, title="Introduction", start_time=0.0, end_time=120.0)
        assert ch.id == 0
        assert ch.title == "Introduction"
        assert ch.start_time == 0.0
        assert ch.end_time == 120.0
    
    def test_chapter_duration(self):
        """Test chapter duration calculation."""
        ch = Chapter(id=0, title="Test", start_time=10.0, end_time=70.0)
        assert ch.duration == 60.0
    
    def test_chapter_duration_zero(self):
        """Test chapter with zero duration."""
        ch = Chapter(id=0, title="Empty", start_time=50.0, end_time=50.0)
        assert ch.duration == 0.0
    
    def test_chapter_str_representation(self):
        """Test chapter string representation."""
        ch = Chapter(id=1, title="The Beginning", start_time=0.0, end_time=300.0)
        result = str(ch)
        assert "The Beginning" in result
        assert "300" in result
    
    def test_chapter_with_special_characters(self):
        """Test chapter with special characters in title."""
        ch = Chapter(id=0, title="Chapter 1: The Hero's Journey", start_time=0.0, end_time=100.0)
        assert ch.title == "Chapter 1: The Hero's Journey"


class TestAudioMetadata:
    """Tests for the AudioMetadata dataclass."""
    
    def test_metadata_creation_minimal(self):
        """Test metadata creation with minimal fields."""
        meta = AudioMetadata()
        assert meta.title is None
        assert meta.artist is None
        assert meta.duration == 0.0
    
    def test_metadata_creation_full(self):
        """Test metadata creation with all fields."""
        meta = AudioMetadata(
            title="The Great Book",
            artist="John Author",
            album="Book Series",
            album_artist="John Author",
            composer="Narrator Name",
            genre="Audiobook",
            date="2024",
            comment="A wonderful story",
            encoder="ffmpeg",
            duration=36000.0,
            bit_rate=128000,
            sample_rate=44100,
            channels=2,
            codec="aac",
            extra_tags={"custom": "value"}
        )
        assert meta.title == "The Great Book"
        assert meta.artist == "John Author"
        assert meta.duration == 36000.0
        assert meta.extra_tags["custom"] == "value"
    
    def test_to_ffmpeg_metadata_full(self):
        """Test conversion to ffmpeg metadata format."""
        meta = AudioMetadata(
            title="Test Book",
            artist="Test Author",
            album="Test Album",
            album_artist="Test Album Artist",
            composer="Test Composer",
            genre="Fiction",
            date="2024",
            comment="Test comment"
        )
        ffmpeg_meta = meta.to_ffmpeg_metadata()
        
        assert ffmpeg_meta["title"] == "Test Book"
        assert ffmpeg_meta["artist"] == "Test Author"
        assert ffmpeg_meta["album"] == "Test Album"
        assert ffmpeg_meta["album_artist"] == "Test Album Artist"
        assert ffmpeg_meta["composer"] == "Test Composer"
        assert ffmpeg_meta["genre"] == "Fiction"
        assert ffmpeg_meta["date"] == "2024"
        assert ffmpeg_meta["comment"] == "Test comment"
    
    def test_to_ffmpeg_metadata_partial(self):
        """Test conversion with only some fields set."""
        meta = AudioMetadata(title="Only Title")
        ffmpeg_meta = meta.to_ffmpeg_metadata()
        
        assert ffmpeg_meta["title"] == "Only Title"
        assert "artist" not in ffmpeg_meta
        assert "album" not in ffmpeg_meta
    
    def test_to_ffmpeg_metadata_with_extra_tags(self):
        """Test that extra tags are included in ffmpeg metadata."""
        meta = AudioMetadata(
            title="Book",
            extra_tags={"narrator": "Voice Actor", "publisher": "AudioCo"}
        )
        ffmpeg_meta = meta.to_ffmpeg_metadata()
        
        assert ffmpeg_meta["title"] == "Book"
        assert ffmpeg_meta["narrator"] == "Voice Actor"
        assert ffmpeg_meta["publisher"] == "AudioCo"


class TestSplitPart:
    """Tests for the SplitPart dataclass."""
    
    @pytest.fixture
    def sample_chapters(self):
        """Create sample chapters for testing."""
        return [
            Chapter(id=0, title="Ch1", start_time=0.0, end_time=100.0),
            Chapter(id=1, title="Ch2", start_time=100.0, end_time=250.0),
            Chapter(id=2, title="Ch3", start_time=250.0, end_time=400.0),
        ]
    
    def test_split_part_creation(self, sample_chapters):
        """Test basic split part creation."""
        part = SplitPart(
            part_number=1,
            total_parts=3,
            chapters=sample_chapters,
            output_path=Path("/tmp/test.m4b")
        )
        assert part.part_number == 1
        assert part.total_parts == 3
        assert len(part.chapters) == 3
    
    def test_split_part_start_time(self, sample_chapters):
        """Test start time property."""
        part = SplitPart(
            part_number=1,
            total_parts=1,
            chapters=sample_chapters,
            output_path=Path("/tmp/test.m4b")
        )
        assert part.start_time == 0.0
    
    def test_split_part_end_time(self, sample_chapters):
        """Test end time property."""
        part = SplitPart(
            part_number=1,
            total_parts=1,
            chapters=sample_chapters,
            output_path=Path("/tmp/test.m4b")
        )
        assert part.end_time == 400.0
    
    def test_split_part_duration(self, sample_chapters):
        """Test duration property."""
        part = SplitPart(
            part_number=1,
            total_parts=1,
            chapters=sample_chapters,
            output_path=Path("/tmp/test.m4b")
        )
        assert part.duration == 400.0
    
    def test_split_part_chapter_titles(self, sample_chapters):
        """Test chapter titles property."""
        part = SplitPart(
            part_number=1,
            total_parts=1,
            chapters=sample_chapters,
            output_path=Path("/tmp/test.m4b")
        )
        assert part.chapter_titles == ["Ch1", "Ch2", "Ch3"]
    
    def test_split_part_empty_chapters(self):
        """Test split part with no chapters."""
        part = SplitPart(
            part_number=1,
            total_parts=1,
            chapters=[],
            output_path=Path("/tmp/test.m4b")
        )
        assert part.start_time == 0.0
        assert part.end_time == 0.0
        assert part.duration == 0.0
        assert part.chapter_titles == []
    
    def test_split_part_str_representation(self, sample_chapters):
        """Test string representation."""
        part = SplitPart(
            part_number=2,
            total_parts=5,
            chapters=sample_chapters,
            output_path=Path("/tmp/test.m4b")
        )
        result = str(part)
        assert "2/5" in result
        assert "3 chapters" in result


class TestSplitResult:
    """Tests for the SplitResult dataclass."""
    
    @pytest.fixture
    def sample_parts(self):
        """Create sample parts for testing."""
        chapters1 = [Chapter(id=0, title="Ch1", start_time=0.0, end_time=100.0)]
        chapters2 = [Chapter(id=1, title="Ch2", start_time=100.0, end_time=200.0)]
        
        return [
            SplitPart(
                part_number=1,
                total_parts=2,
                chapters=chapters1,
                output_path=Path("/tmp/part1.m4b")
            ),
            SplitPart(
                part_number=2,
                total_parts=2,
                chapters=chapters2,
                output_path=Path("/tmp/part2.m4b")
            ),
        ]
    
    def test_split_result_success(self, sample_parts):
        """Test successful split result."""
        result = SplitResult(
            source_file=Path("/tmp/source.m4b"),
            parts=sample_parts,
            original_metadata=AudioMetadata(title="Test"),
            success=True
        )
        assert result.success
        assert result.error_message is None
        assert len(result.parts) == 2
    
    def test_split_result_failure(self):
        """Test failed split result."""
        result = SplitResult(
            source_file=Path("/tmp/source.m4b"),
            parts=[],
            original_metadata=AudioMetadata(),
            success=False,
            error_message="File not found"
        )
        assert not result.success
        assert result.error_message == "File not found"
    
    def test_output_files_property(self, sample_parts):
        """Test output files property."""
        result = SplitResult(
            source_file=Path("/tmp/source.m4b"),
            parts=sample_parts,
            original_metadata=AudioMetadata(),
            success=True
        )
        output_files = result.output_files
        assert len(output_files) == 2
        assert output_files[0] == Path("/tmp/part1.m4b")
        assert output_files[1] == Path("/tmp/part2.m4b")
    
    def test_str_representation_success(self, sample_parts):
        """Test string representation for success."""
        result = SplitResult(
            source_file=Path("/tmp/source.m4b"),
            parts=sample_parts,
            original_metadata=AudioMetadata(),
            success=True
        )
        result_str = str(result)
        assert "source.m4b" in result_str
        assert "2 parts" in result_str
    
    def test_str_representation_failure(self):
        """Test string representation for failure."""
        result = SplitResult(
            source_file=Path("/tmp/source.m4b"),
            parts=[],
            original_metadata=AudioMetadata(),
            success=False,
            error_message="Something went wrong"
        )
        result_str = str(result)
        assert "Failed" in result_str
        assert "Something went wrong" in result_str
