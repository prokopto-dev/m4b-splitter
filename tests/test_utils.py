import subprocess
import tempfile
from pathlib import Path


def create_test_m4b(
    output_path: Path,
    num_chapters: int = 3,
    chapter_duration: float = 60.0,
    title: str = "Test Audiobook",
    artist: str = "Test Author",
) -> bool:
    """
    Create a test M4B file with chapters.

    Args:
        output_path: Path for the output file.
        num_chapters: Number of chapters to create.
        chapter_duration: Duration of each chapter in seconds.
        title: Book title.
        artist: Author name.

    Returns:
        True if successful.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create silence audio
        total_duration = num_chapters * chapter_duration
        audio_file = temp_path / "audio.m4a"

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            str(total_duration),
            "-c:a",
            "aac",
            "-b:a",
            "64k",
            str(audio_file),
        ]

        result = subprocess.run(cmd, check=False, capture_output=True)
        if result.returncode != 0:
            return False

        # Create metadata file with chapters
        metadata_file = temp_path / "metadata.txt"
        with metadata_file.open("w") as f:
            f.write(";FFMETADATA1\n")
            f.write(f"title={title}\n")
            f.write(f"artist={artist}\n")
            f.write("album=Test Album\n")
            f.write("genre=Audiobook\n")

            for i in range(num_chapters):
                start_ms = int(i * chapter_duration * 1000)
                end_ms = int((i + 1) * chapter_duration * 1000)
                f.write("\n[CHAPTER]\n")
                f.write("TIMEBASE=1/1000\n")
                f.write(f"START={start_ms}\n")
                f.write(f"END={end_ms}\n")
                f.write(f"title=Chapter {i + 1}\n")

        # Combine audio with metadata
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(audio_file),
            "-i",
            str(metadata_file),
            "-map",
            "0:a",
            "-map_metadata",
            "1",
            "-map_chapters",
            "1",
            "-c",
            "copy",
            "-f",
            "ipod",
            str(output_path),
        ]

        result = subprocess.run(cmd, check=False, capture_output=True)
        return result.returncode == 0 and output_path.exists()
