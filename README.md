# M4B Splitter

A Python package for splitting M4B audiobook files into smaller parts at chapter boundaries while preserving metadata.

## Features

- **Chapter-aware splitting**: Splits only at chapter boundaries, never in the middle of a chapter
- **Metadata preservation**: Maintains all original metadata (title, artist, album, etc.)
- **Chapter information**: Preserves chapter titles with adjusted timestamps in each part
- **Cover art**: Extracts and embeds cover art in all output files
- **Progress tracking**: Real-time progress display with detailed step information
- **No re-encoding**: Uses stream copying for fast, lossless splitting (by default)
- **iPod Classic support**: Optional re-encoding for iPod Classic compatibility
- **Dependency checking**: Detects OS and provides installation instructions for ffmpeg
- **Flexible naming**: Customizable output filename patterns
- **Python 3.12+**: Uses modern Python features for clean, type-safe code

## Requirements

- Python 3.12 or higher
- `ffmpeg` and `ffprobe` installed and available in PATH

### Checking Dependencies

Run the built-in dependency check to verify ffmpeg is installed:

```bash
m4b-splitter check
```

This will show whether ffmpeg/ffprobe are installed, and if not, provide OS-specific installation instructions.

### Installing ffmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS (Homebrew):**
```bash
brew install ffmpeg
```

**Windows (Chocolatey):**
```bash
choco install ffmpeg
```

**Fedora:**
```bash
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

## Installation

### From source

```bash
git clone https://github.com/example/m4b-splitter.git
cd m4b-splitter
pip install -e .
```

### Using pip (when published)

```bash
pip install m4b-splitter
```

## Usage

### Command Line Interface

Basic usage - split an audiobook with default 8-hour maximum per part:

```bash
m4b-splitter audiobook.m4b
```

Specify maximum duration and output directory:

```bash
m4b-splitter audiobook.m4b -d 4h -o ./split_output
```

Duration formats supported:
- Hours: `8h`, `4.5h`, `2`
- Minutes: `90m`, `120m`
- Combined: `2h30m`

Custom output filename pattern:

```bash
m4b-splitter audiobook.m4b -p "{title} - Part {part}/{total}.m4b"
```

Available placeholders:
- `{title}` - Book title from metadata
- `{artist}` - Author/artist from metadata
- `{part}` - Part number
- `{total}` - Total number of parts

Quiet mode (suppress progress output):

```bash
m4b-splitter audiobook.m4b -q
```

### iPod Classic Mode

For compatibility with iPod Classic devices, use the `--ipod` flag to re-encode audio:

```bash
m4b-splitter audiobook.m4b --ipod
```

The iPod Classic has a 32-bit sample counter limitation that restricts playback duration. The `--ipod` flag re-encodes audio to work around this.

**iPod Presets:**

| Preset | Sample Rate | Bitrate | Channels | Max Duration |
|--------|-------------|---------|----------|--------------|
| standard | 22050 Hz | 64 kbps | Mono | ~55 hours |
| high | 44100 Hz | 128 kbps | Stereo | ~27 hours |
| extended | 16000 Hz | 48 kbps | Mono | ~74 hours |

Use a specific preset:

```bash
m4b-splitter audiobook.m4b --ipod --ipod-preset high
```

**Note:** iPod mode requires re-encoding, which is slower than the default stream copy mode but produces smaller files optimized for the device.

### Python API

#### Simple usage

```python
from m4b_splitter import split_m4b

# Split with default settings (8-hour max per part)
result = split_m4b("audiobook.m4b", "./output")

# Check result
if result.success:
    print(f"Created {len(result.parts)} parts:")
    for path in result.output_files:
        print(f"  {path}")
else:
    print(f"Failed: {result.error_message}")
```

#### iPod mode

```python
from m4b_splitter import split_m4b

# Split with iPod-compatible encoding
result = split_m4b(
    "audiobook.m4b",
    "./output",
    max_duration_hours=4,
    ipod_mode=True,
    ipod_preset="standard"  # or "high" or "extended"
)
```

#### Advanced usage with custom progress

```python
from pathlib import Path
from m4b_splitter import (
    M4BSplitter,
    ConsoleProgress,
    ProgressCallback,
    ProgressUpdate,
)

# Use built-in console progress
splitter = M4BSplitter(progress_callback=ConsoleProgress())

result = splitter.split(
    input_file=Path("audiobook.m4b"),
    output_dir=Path("./output"),
    max_duration_hours=4.0,
    output_pattern="{title} - Part {part} of {total}.m4b",
    ipod_mode=True
)

# Access detailed result information
print(f"Source: {result.source_file}")
print(f"Original title: {result.original_metadata.title}")
print(f"Original artist: {result.original_metadata.artist}")

for part in result.parts:
    print(f"\nPart {part.part_number}/{part.total_parts}:")
    print(f"  Duration: {part.duration:.1f}s")
    print(f"  Chapters: {len(part.chapters)}")
    for ch in part.chapters:
        print(f"    - {ch.title}")
```

#### Custom progress callback

```python
from m4b_splitter import M4BSplitter, ProgressCallback, ProgressUpdate

class MyProgress(ProgressCallback):
    def on_progress(self, update: ProgressUpdate) -> None:
        if update.total > 0:
            percent = (update.current / update.total) * 100
            print(f"[{percent:.0f}%] {update.message}")
        else:
            print(update.message)
    
    def on_complete(self, success: bool, message: str) -> None:
        status = "SUCCESS" if success else "FAILED"
        print(f"[{status}] {message}")
    
    def on_error(self, error: str) -> None:
        print(f"[ERROR] {error}")

splitter = M4BSplitter(progress_callback=MyProgress())
result = splitter.split("audiobook.m4b", "./output")
```

#### Checking dependencies programmatically

```python
from m4b_splitter import check_dependencies, format_dependency_check

# Check if ffmpeg is available
result = check_dependencies()

if result.all_found:
    print("All dependencies satisfied!")
    print(f"ffmpeg: {result.ffmpeg.path}")
    print(f"ffprobe: {result.ffprobe.path}")
else:
    # Print detailed instructions
    print(format_dependency_check(result))
```

#### Probing files without splitting

```python
from m4b_splitter import extract_chapters, extract_metadata, validate_m4b_file
from pathlib import Path

file_path = Path("audiobook.m4b")

# Validate file
is_valid, message = validate_m4b_file(file_path)
print(f"Valid: {is_valid} - {message}")

# Get metadata
metadata = extract_metadata(file_path)
print(f"Title: {metadata.title}")
print(f"Artist: {metadata.artist}")
print(f"Duration: {metadata.duration / 3600:.1f} hours")

# Get chapters
chapters = extract_chapters(file_path)
print(f"\nChapters ({len(chapters)}):")
for ch in chapters:
    print(f"  {ch.id + 1}. {ch.title} ({ch.duration:.0f}s)")
```

## Output

Each output file will:

1. Contain complete chapters (never split mid-chapter)
2. Have a title like "Original Title - Part 1/3"
3. Include all original metadata with track number set to part/total
4. Have chapter markers with timestamps adjusted to start from 0
5. Include embedded cover art (if present in source)

With `--ipod` mode, files are also:
- Re-encoded with optimized settings for iPod Classic
- Smaller in file size (especially with mono/lower bitrate)
- Compatible with the iPod's 32-bit sample counter limitation

## Project Structure

```
m4b_splitter/
├── src/
│   └── m4b_splitter/
│       ├── __init__.py      # Package exports
│       ├── __main__.py      # Entry point for python -m
│       ├── cli.py           # Command-line interface
│       ├── dependencies.py  # FFmpeg dependency checking
│       ├── models.py        # Data models (Chapter, Metadata, etc.)
│       ├── probe.py         # ffprobe wrapper for metadata extraction
│       ├── progress.py      # Progress tracking and display
│       └── splitter.py      # Core splitting logic
├── tests/                   # Test files
├── pyproject.toml          # Package configuration
└── README.md               # This file
```

## How It Works

1. **Dependency Check**: Verify ffmpeg/ffprobe are available
2. **Validation**: Verify the input file exists and contains chapters
3. **Metadata Extraction**: Use ffprobe to extract all metadata and chapter information
4. **Planning**: Calculate split points based on chapter boundaries and max duration
5. **Cover Art**: Extract any embedded cover art for reuse
6. **Splitting**: For each part:
   - Generate an ffmpeg metadata file with adjusted chapter times
   - Use ffmpeg to extract the audio segment (stream copy or re-encode for iPod)
   - Embed metadata and cover art
7. **Output**: Return structured result with all file paths and information

## Limitations

- Requires chapters to be present in the M4B file
- Single chapters longer than max duration will be placed in their own part
- Cover art must be in a format ffmpeg can extract (usually JPEG)
- iPod mode requires re-encoding, which is slower than stream copy

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
