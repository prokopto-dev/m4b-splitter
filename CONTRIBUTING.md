# Contributing to M4B Splitter

Thank you for your interest in contributing to M4B Splitter! This document provides guidelines and information for contributors.

## Development Setup

### Prerequisites

- Python 3.12 or higher
- ffmpeg and ffprobe installed and in PATH
- Git

### Setting Up Your Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/m4b-splitter.git
   cd m4b-splitter
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify your setup:**
   ```bash
   m4b-splitter check
   pytest tests/ -v
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=m4b_splitter --cov-report=html

# Run specific test file
pytest tests/test_splitter.py -v

# Run tests matching a pattern
pytest tests/ -v -k "ipod"

# Skip integration tests (faster)
pytest tests/ -v -k "not Integration"
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code
ruff format src/ tests/

# Check for linting issues
ruff check src/ tests/

# Fix auto-fixable issues
ruff check src/ tests/ --fix

# Type checking
mypy src/m4b_splitter
```

### Pre-commit Checks

Before committing, ensure:

1. All tests pass: `pytest tests/ -v`
2. Code is formatted: `ruff format src/ tests/`
3. No linting errors: `ruff check src/ tests/`
4. Type hints are correct: `mypy src/m4b_splitter`

## Project Structure

```
m4b-splitter/
├── src/
│   └── m4b_splitter/
│       ├── __init__.py      # Package exports
│       ├── __main__.py      # Entry point for python -m
│       ├── cli.py           # Typer/Rich CLI
│       ├── dependencies.py  # ffmpeg dependency checking
│       ├── models.py        # Data classes
│       ├── probe.py         # ffprobe wrapper
│       └── splitter.py      # Core splitting logic
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_cli.py
│   ├── test_dependencies.py
│   ├── test_integration.py  # Requires ffmpeg
│   ├── test_models.py
│   └── test_splitter.py
├── .github/
│   └── workflows/
│       ├── ci.yml           # Main CI pipeline
│       └── release.yml      # PyPI publishing
├── pyproject.toml           # Project configuration
└── README.md
```

## Making Changes

### Branching Strategy

- `main` - Stable release branch
- `develop` - Development branch
- Feature branches: `feature/description`
- Bug fixes: `fix/description`

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add iPod Video preset for 5th gen compatibility
fix: preserve metadata in all split parts
docs: update README with new CLI options
test: add integration tests for metadata propagation
```

### Pull Requests

1. Create a feature branch from `develop`
2. Make your changes
3. Add/update tests as needed
4. Ensure all tests pass
5. Update documentation if needed
6. Submit a pull request to `develop`

## Adding New Features

### Adding a New iPod Preset

1. Add the preset factory method to `IPodSettings` in `splitter.py`:
   ```python
   @classmethod
   def my_preset(cls) -> "IPodSettings":
       return cls(
           sample_rate=22050,
           bitrate=64,
           channels=1,
           preset_name="my_preset"
       )
   ```

2. Add to `IPOD_PRESETS` dictionary:
   ```python
   IPOD_PRESETS = {
       ...
       "my_preset": IPodSettings.my_preset(),
   }
   ```

3. Add to CLI `PresetChoice` enum in `cli.py`

4. Add tests in `test_splitter.py`

5. Update README documentation

### Adding New Metadata Fields

1. Update `AudioMetadata` in `models.py`
2. Update `extract_metadata()` in `probe.py`
3. Update `create_metadata_file()` in `splitter.py`
4. Add tests

## Reporting Issues

When reporting issues, please include:

- Python version (`python --version`)
- ffmpeg version (`ffmpeg -version`)
- Operating system
- Complete error message/traceback
- Minimal example to reproduce the issue

## Questions?

Feel free to open an issue for questions or discussions about the project.
