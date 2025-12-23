"""Unit tests for the splitter module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m4b_splitter.models import Chapter
from m4b_splitter.splitter import (
    IPOD_PRESETS,
    FFmpegProgress,
    IPodSettings,
    format_time,
    format_time_human,
    parse_ffmpeg_progress,
    plan_splits,
    sanitize_filename,
)


class TestFormatTime:
    """Tests for the format_time function."""

    def test_format_zero(self):
        """Test formatting zero seconds."""
        assert format_time(0) == "00:00:00.000"

    def test_format_seconds_only(self):
        """Test formatting seconds only."""
        assert format_time(45.5) == "00:00:45.500"

    def test_format_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_time(125.25) == "00:02:05.250"

    def test_format_hours_minutes_seconds(self):
        """Test formatting with hours."""
        assert format_time(3661.123) == "01:01:01.123"

    def test_format_large_duration(self):
        """Test formatting large durations."""
        # 10 hours, 30 minutes, 45.678 seconds
        seconds = 10 * 3600 + 30 * 60 + 45.678
        assert format_time(seconds) == "10:30:45.678"

    def test_format_precision(self):
        """Test millisecond precision."""
        assert format_time(1.001) == "00:00:01.001"
        assert format_time(1.999) == "00:00:01.999"


class TestFormatTimeHuman:
    """Tests for the format_time_human function."""

    def test_format_seconds_only(self):
        """Test formatting seconds only."""
        assert format_time_human(30) == "30s"
        assert format_time_human(59) == "59s"

    def test_format_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_time_human(90) == "1m 30s"
        assert format_time_human(125) == "2m 5s"

    def test_format_hours_minutes_seconds(self):
        """Test formatting hours, minutes, and seconds."""
        assert format_time_human(3661) == "1h 1m 1s"
        assert format_time_human(7200) == "2h 0m 0s"

    def test_format_zero(self):
        """Test formatting zero seconds."""
        assert format_time_human(0) == "0s"


class TestSanitizeFilename:
    """Tests for the sanitize_filename function."""

    def test_clean_filename(self):
        """Test filename that needs no changes."""
        assert sanitize_filename("My Audiobook") == "My Audiobook"

    def test_remove_invalid_characters(self):
        """Test removal of invalid characters."""
        assert sanitize_filename('Book: Part 1') == "Book_ Part 1"
        assert sanitize_filename('Book/Part') == "Book_Part"
        assert sanitize_filename('Book\\Part') == "Book_Part"
        assert sanitize_filename('Book<>Part') == "Book__Part"
        assert sanitize_filename('Book"Part') == "Book_Part"
        assert sanitize_filename('Book|Part') == "Book_Part"
        assert sanitize_filename('Book?Part') == "Book_Part"
        assert sanitize_filename('Book*Part') == "Book_Part"

    def test_strip_whitespace_and_dots(self):
        """Test stripping of leading/trailing whitespace and dots."""
        assert sanitize_filename("  Book  ") == "Book"
        assert sanitize_filename("...Book...") == "Book"
        assert sanitize_filename(". Book .") == "Book"

    def test_empty_string(self):
        """Test empty string returns 'untitled'."""
        assert sanitize_filename("") == "untitled"
        assert sanitize_filename("   ") == "untitled"
        assert sanitize_filename("...") == "untitled"

    def test_length_limit(self):
        """Test filename length limiting."""
        long_name = "A" * 250
        result = sanitize_filename(long_name)
        assert len(result) == 200

    def test_unicode_characters(self):
        """Test that unicode characters are preserved."""
        assert sanitize_filename("Bücher") == "Bücher"
        assert sanitize_filename("日本語") == "日本語"

    def test_slash_in_pattern(self):
        """Test that slashes are replaced (important for Part X/Y patterns)."""
        assert sanitize_filename("Part 1/3") == "Part 1_3"
        assert sanitize_filename("Book - Part 2/5.m4b") == "Book - Part 2_5.m4b"


class TestPlanSplits:
    """Tests for the plan_splits function."""

    def test_empty_chapters(self):
        """Test with no chapters."""
        parts = plan_splits([], max_duration_seconds=3600)
        assert len(parts) == 0

    def test_single_chapter_under_limit(self):
        """Test single chapter under the limit."""
        chapters = [Chapter(id=0, title="Ch1", start_time=0.0, end_time=100.0)]
        parts = plan_splits(chapters, max_duration_seconds=3600)

        assert len(parts) == 1
        assert len(parts[0]) == 1

    def test_multiple_chapters_under_limit(self):
        """Test multiple chapters that fit in one part."""
        chapters = [
            Chapter(id=0, title="Ch1", start_time=0.0, end_time=100.0),
            Chapter(id=1, title="Ch2", start_time=100.0, end_time=200.0),
            Chapter(id=2, title="Ch3", start_time=200.0, end_time=300.0),
        ]
        parts = plan_splits(chapters, max_duration_seconds=3600)

        assert len(parts) == 1
        assert len(parts[0]) == 3

    def test_split_into_two_parts(self):
        """Test splitting into exactly two parts."""
        chapters = [
            Chapter(id=0, title="Ch1", start_time=0.0, end_time=100.0),
            Chapter(id=1, title="Ch2", start_time=100.0, end_time=200.0),
            Chapter(id=2, title="Ch3", start_time=200.0, end_time=300.0),
            Chapter(id=3, title="Ch4", start_time=300.0, end_time=400.0),
        ]
        # Max 250s means Ch1+Ch2 (200s) in part 1, Ch3+Ch4 (200s) in part 2
        parts = plan_splits(chapters, max_duration_seconds=250)

        assert len(parts) == 2
        assert len(parts[0]) == 2  # Ch1, Ch2
        assert len(parts[1]) == 2  # Ch3, Ch4

    def test_split_into_multiple_parts(self):
        """Test splitting into multiple parts."""
        chapters = [
            Chapter(id=i, title=f"Ch{i+1}", start_time=i*60.0, end_time=(i+1)*60.0)
            for i in range(10)
        ]
        # 10 chapters of 60s each, max 150s per part
        parts = plan_splits(chapters, max_duration_seconds=150)

        # Should be 5 parts with 2 chapters each
        assert len(parts) == 5
        for part in parts:
            assert len(part) == 2

    def test_large_chapter_exceeds_limit(self):
        """Test chapter larger than max duration gets its own part."""
        chapters = [
            Chapter(id=0, title="Ch1", start_time=0.0, end_time=50.0),
            Chapter(id=1, title="Ch2 (Long)", start_time=50.0, end_time=200.0),  # 150s
            Chapter(id=2, title="Ch3", start_time=200.0, end_time=250.0),
        ]
        # Max 100s, but Ch2 is 150s
        parts = plan_splits(chapters, max_duration_seconds=100)

        # Ch1 alone, Ch2 alone (exceeds but can't split), Ch3 alone
        assert len(parts) == 3
        assert parts[0][0].title == "Ch1"
        assert parts[1][0].title == "Ch2 (Long)"
        assert parts[2][0].title == "Ch3"

    def test_preserves_chapter_order(self):
        """Test that chapter order is preserved."""
        chapters = [
            Chapter(id=0, title="First", start_time=0.0, end_time=50.0),
            Chapter(id=1, title="Second", start_time=50.0, end_time=100.0),
            Chapter(id=2, title="Third", start_time=100.0, end_time=150.0),
        ]
        parts = plan_splits(chapters, max_duration_seconds=75)

        assert parts[0][0].title == "First"
        assert parts[1][0].title == "Second"
        assert parts[2][0].title == "Third"


class TestFFmpegProgress:
    """Tests for FFmpegProgress dataclass."""

    def test_default_values(self):
        """Test default progress values."""
        prog = FFmpegProgress()
        assert prog.frame == 0
        assert prog.fps == 0.0
        assert prog.size_kb == 0
        assert prog.time_seconds == 0.0
        assert prog.bitrate_kbps == 0.0
        assert prog.speed == 0.0
        assert prog.percent == 0.0

    def test_custom_values(self):
        """Test progress with custom values."""
        prog = FFmpegProgress(
            time_seconds=60.0,
            percent=50.0,
            speed=2.5,
            bitrate_kbps=128.0,
            size_kb=1024
        )
        assert prog.time_seconds == 60.0
        assert prog.percent == 50.0
        assert prog.speed == 2.5
        assert prog.bitrate_kbps == 128.0
        assert prog.size_kb == 1024


class TestParseFFmpegProgress:
    """Tests for parse_ffmpeg_progress function."""

    def test_parse_time(self):
        """Test parsing time from ffmpeg output."""
        line = "frame=  100 fps=50.0 size=    512kB time=00:01:30.50 bitrate= 128.0kbits/s speed=2.00x"
        prog = parse_ffmpeg_progress(line, total_duration=180.0)

        assert prog is not None
        assert prog.time_seconds == pytest.approx(90.5, abs=0.1)
        assert prog.percent == pytest.approx(50.28, abs=0.5)

    def test_parse_size(self):
        """Test parsing size from ffmpeg output."""
        line = "size=  1024kB time=00:01:00.00"
        prog = parse_ffmpeg_progress(line, total_duration=120.0)

        assert prog is not None
        assert prog.size_kb == 1024

    def test_parse_bitrate(self):
        """Test parsing bitrate from ffmpeg output."""
        line = "time=00:01:00.00 bitrate= 128.5kbits/s"
        prog = parse_ffmpeg_progress(line, total_duration=120.0)

        assert prog is not None
        assert prog.bitrate_kbps == pytest.approx(128.5, abs=0.1)

    def test_parse_speed(self):
        """Test parsing speed from ffmpeg output."""
        line = "time=00:01:00.00 speed=2.50x"
        prog = parse_ffmpeg_progress(line, total_duration=120.0)

        assert prog is not None
        assert prog.speed == pytest.approx(2.5, abs=0.1)

    def test_no_time_returns_none(self):
        """Test that lines without time= return None."""
        line = "Input #0, mov,mp4,m4a,3gp,3g2,mj2"
        prog = parse_ffmpeg_progress(line, total_duration=120.0)

        assert prog is None

    def test_percent_calculation(self):
        """Test percentage calculation."""
        line = "time=00:00:30.00"
        prog = parse_ffmpeg_progress(line, total_duration=60.0)

        assert prog is not None
        assert prog.percent == pytest.approx(50.0, abs=0.1)

    def test_percent_capped_at_100(self):
        """Test that percentage doesn't exceed 100."""
        line = "time=00:02:00.00"
        prog = parse_ffmpeg_progress(line, total_duration=60.0)

        assert prog is not None
        assert prog.percent == 100.0


class TestIPodSettings:
    """Tests for the IPodSettings dataclass."""

    def test_default_settings(self):
        """Test default iPod settings."""
        settings = IPodSettings()
        assert settings.sample_rate == 22050
        assert settings.bitrate == 64
        assert settings.channels == 1
        assert settings.encoder == "aac"

    def test_standard_preset(self):
        """Test standard preset."""
        settings = IPodSettings.standard()
        assert settings.sample_rate == 22050
        assert settings.bitrate == 64
        assert settings.channels == 1
        assert not settings.use_cbr
        assert settings.preset_name == "standard"

    def test_high_quality_preset(self):
        """Test high quality preset."""
        settings = IPodSettings.high_quality()
        assert settings.sample_rate == 44100
        assert settings.bitrate == 128
        assert settings.channels == 2
        assert settings.preset_name == "high"

    def test_extended_duration_preset(self):
        """Test extended duration preset."""
        settings = IPodSettings.extended_duration()
        assert settings.sample_rate == 16000
        assert settings.bitrate == 48
        assert settings.channels == 1
        assert settings.preset_name == "extended"

    def test_ipod_video_preset(self):
        """Test iPod Video (5th Gen) preset."""
        settings = IPodSettings.ipod_video()
        assert settings.sample_rate == 44100
        assert settings.bitrate == 80
        assert settings.channels == 1
        assert settings.use_cbr
        assert settings.preset_name == "video"

    def test_max_duration_calculation(self):
        """Test max duration calculation."""
        settings = IPodSettings(sample_rate=22050)
        max_hours = settings.max_duration_hours

        # Should be approximately 54 hours for 22050Hz
        assert 50 < max_hours < 60

    def test_max_duration_varies_with_sample_rate(self):
        """Test that max duration varies inversely with sample rate."""
        low_rate = IPodSettings(sample_rate=16000)
        high_rate = IPodSettings(sample_rate=44100)

        # Lower sample rate should allow longer duration
        assert low_rate.max_duration_hours > high_rate.max_duration_hours

    def test_str_representation(self):
        """Test string representation."""
        settings = IPodSettings(sample_rate=22050, bitrate=64, channels=1, preset_name="test")
        result = str(settings)

        assert "22050Hz" in result
        assert "64kbps" in result
        assert "mono" in result

    def test_str_representation_stereo(self):
        """Test string representation for stereo."""
        settings = IPodSettings(channels=2, preset_name="test")
        result = str(settings)

        assert "stereo" in result

    def test_str_representation_cbr(self):
        """Test string representation shows CBR when enabled."""
        settings = IPodSettings(use_cbr=True, preset_name="test")
        result = str(settings)

        assert "CBR" in result

    def test_get_ffmpeg_audio_args(self):
        """Test ffmpeg argument generation."""
        settings = IPodSettings(sample_rate=44100, bitrate=80, channels=1, preset_name="test")
        args = settings.get_ffmpeg_audio_args()

        assert "-c:a" in args
        assert "aac" in args
        assert "-ar" in args
        assert "44100" in args
        assert "-ac" in args
        assert "1" in args
        assert "-b:a" in args
        assert "80k" in args

    def test_get_ffmpeg_audio_args_cbr(self):
        """Test ffmpeg argument generation with CBR."""
        settings = IPodSettings(use_cbr=True, preset_name="test")
        args = settings.get_ffmpeg_audio_args()

        # Should include profile for CBR
        assert "-profile:a" in args


class TestIPodPresets:
    """Tests for the IPOD_PRESETS dictionary."""

    def test_presets_exist(self):
        """Test that all expected presets exist."""
        assert "standard" in IPOD_PRESETS
        assert "high" in IPOD_PRESETS
        assert "extended" in IPOD_PRESETS
        assert "video" in IPOD_PRESETS

    def test_presets_are_ipod_settings(self):
        """Test that presets are IPodSettings instances."""
        for name, preset in IPOD_PRESETS.items():
            assert isinstance(preset, IPodSettings), f"{name} is not IPodSettings"

    def test_preset_names_match(self):
        """Test that preset names match their keys."""
        for name, preset in IPOD_PRESETS.items():
            assert preset.preset_name == name

    def test_preset_quality_ordering(self):
        """Test that presets have expected quality ordering."""
        standard = IPOD_PRESETS["standard"]
        high = IPOD_PRESETS["high"]
        extended = IPOD_PRESETS["extended"]
        video = IPOD_PRESETS["video"]

        # High should have highest bitrate
        assert high.bitrate > standard.bitrate
        assert high.bitrate > extended.bitrate

        # Extended should have longest max duration
        assert extended.max_duration_hours > standard.max_duration_hours
        assert extended.max_duration_hours > high.max_duration_hours

        # Video should use CBR
        assert video.use_cbr
        assert not standard.use_cbr
