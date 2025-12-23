"""Unit tests for the dependencies module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import subprocess

from m4b_splitter.dependencies import (
    DependencyCheckResult,
    DependencyStatus,
    OSType,
    check_dependencies,
    check_dependency,
    detect_os,
    format_dependency_check,
    get_installation_instructions,
    get_version,
)


class TestOSType:
    """Tests for the OSType enum."""

    def test_all_os_types_exist(self):
        """Test that all expected OS types are defined."""
        assert OSType.LINUX_DEBIAN
        assert OSType.LINUX_REDHAT
        assert OSType.LINUX_ARCH
        assert OSType.LINUX_SUSE
        assert OSType.LINUX_ALPINE
        assert OSType.LINUX_OTHER
        assert OSType.MACOS
        assert OSType.WINDOWS
        assert OSType.UNKNOWN


class TestDependencyStatus:
    """Tests for the DependencyStatus dataclass."""

    def test_found_dependency(self):
        """Test creating a found dependency status."""
        status = DependencyStatus(
            name="ffmpeg",
            found=True,
            path="/usr/bin/ffmpeg",
            version="ffmpeg version 6.0",
        )
        assert status.name == "ffmpeg"
        assert status.found
        assert status.path == "/usr/bin/ffmpeg"
        assert status.version == "ffmpeg version 6.0"

    def test_not_found_dependency(self):
        """Test creating a not found dependency status."""
        status = DependencyStatus(name="ffmpeg", found=False)
        assert status.name == "ffmpeg"
        assert not status.found
        assert status.path is None
        assert status.version is None


class TestDependencyCheckResult:
    """Tests for the DependencyCheckResult dataclass."""

    def test_all_found(self):
        """Test when all dependencies are found."""
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(name="ffmpeg", found=True, path="/usr/bin/ffmpeg"),
            ffprobe=DependencyStatus(
                name="ffprobe", found=True, path="/usr/bin/ffprobe"
            ),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )
        assert result.all_found
        assert result.missing == []

    def test_ffmpeg_missing(self):
        """Test when ffmpeg is missing."""
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(name="ffmpeg", found=False),
            ffprobe=DependencyStatus(
                name="ffprobe", found=True, path="/usr/bin/ffprobe"
            ),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )
        assert not result.all_found
        assert "ffmpeg" in result.missing
        assert "ffprobe" not in result.missing

    def test_ffprobe_missing(self):
        """Test when ffprobe is missing."""
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(name="ffmpeg", found=True, path="/usr/bin/ffmpeg"),
            ffprobe=DependencyStatus(name="ffprobe", found=False),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )
        assert not result.all_found
        assert "ffprobe" in result.missing
        assert "ffmpeg" not in result.missing

    def test_both_missing(self):
        """Test when both dependencies are missing."""
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(name="ffmpeg", found=False),
            ffprobe=DependencyStatus(name="ffprobe", found=False),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )
        assert not result.all_found
        assert "ffmpeg" in result.missing
        assert "ffprobe" in result.missing


class TestDetectOS:
    """Tests for the detect_os function."""

    @patch("platform.system")
    @patch("platform.mac_ver")
    def test_detect_macos(self, mock_mac_ver, mock_system):
        """Test detecting macOS."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("14.0", ("", "", ""), "")

        os_type, os_name = detect_os()

        assert os_type == OSType.MACOS
        assert "macOS" in os_name

    @patch("platform.system")
    @patch("platform.win32_ver")
    def test_detect_windows(self, mock_win32_ver, mock_system):
        """Test detecting Windows."""
        mock_system.return_value = "Windows"
        mock_win32_ver.return_value = ("10", "10.0.19041", "", "")

        os_type, os_name = detect_os()

        assert os_type == OSType.WINDOWS
        assert "Windows" in os_name

    @patch("platform.system")
    @patch("builtins.open")
    def test_detect_ubuntu(self, mock_open, mock_system):
        """Test detecting Ubuntu."""
        mock_system.return_value = "Linux"
        mock_open.return_value.__enter__.return_value = iter(
            [
                "ID=ubuntu\n",
                "ID_LIKE=debian\n",
                'PRETTY_NAME="Ubuntu 24.04 LTS"\n',
            ]
        )

        os_type, os_name = detect_os()

        assert os_type == OSType.LINUX_DEBIAN

    @patch("platform.system")
    @patch("builtins.open")
    def test_detect_fedora(self, mock_open, mock_system):
        """Test detecting Fedora."""
        mock_system.return_value = "Linux"
        mock_open.return_value.__enter__.return_value = iter(
            [
                "ID=fedora\n",
                'PRETTY_NAME="Fedora Linux 39"\n',
            ]
        )

        os_type, os_name = detect_os()

        assert os_type == OSType.LINUX_REDHAT

    @patch("platform.system")
    @patch("builtins.open")
    def test_detect_arch(self, mock_open, mock_system):
        """Test detecting Arch Linux."""
        mock_system.return_value = "Linux"
        mock_open.return_value.__enter__.return_value = iter(
            [
                "ID=arch\n",
                'PRETTY_NAME="Arch Linux"\n',
            ]
        )

        os_type, os_name = detect_os()

        assert os_type == OSType.LINUX_ARCH

    @patch("platform.system")
    def test_detect_unknown(self, mock_system):
        """Test detecting unknown OS."""
        mock_system.return_value = "SomeUnknownOS"

        os_type, os_name = detect_os()

        assert os_type == OSType.UNKNOWN


class TestGetVersion:
    """Tests for the get_version function."""

    @patch("subprocess.run")
    def test_get_version_success(self, mock_run):
        """Test getting version successfully."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ffmpeg version 6.0 Copyright (c) 2000-2023\nmore info"
        )

        version = get_version("/usr/bin/ffmpeg")

        assert version == "ffmpeg version 6.0 Copyright (c) 2000-2023"

    @patch("subprocess.run")
    def test_get_version_failure(self, mock_run):
        """Test getting version when command fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        version = get_version("/usr/bin/nonexistent")

        assert version is None

    @patch("subprocess.run")
    def test_get_version_timeout(self, mock_run):
        """Test getting version when command times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="test", timeout=10)

        version = get_version("/usr/bin/ffmpeg")

        assert version is None

    @patch("subprocess.run")
    def test_get_version_not_found(self, mock_run):
        """Test getting version when file not found."""
        mock_run.side_effect = FileNotFoundError()

        version = get_version("/nonexistent/path")

        assert version is None


class TestCheckDependency:
    """Tests for the check_dependency function."""

    @patch("shutil.which")
    @patch("m4b_splitter.dependencies.get_version")
    def test_dependency_found(self, mock_get_version, mock_which):
        """Test checking a found dependency."""
        mock_which.return_value = "/usr/bin/ffmpeg"
        mock_get_version.return_value = "ffmpeg version 6.0"

        status = check_dependency("ffmpeg")

        assert status.name == "ffmpeg"
        assert status.found
        assert status.path == "/usr/bin/ffmpeg"
        assert status.version == "ffmpeg version 6.0"

    @patch("shutil.which")
    def test_dependency_not_found(self, mock_which):
        """Test checking a missing dependency."""
        mock_which.return_value = None

        status = check_dependency("nonexistent")

        assert status.name == "nonexistent"
        assert not status.found
        assert status.path is None


class TestGetInstallationInstructions:
    """Tests for the get_installation_instructions function."""

    def test_debian_instructions(self):
        """Test Debian installation instructions."""
        instructions = get_installation_instructions(OSType.LINUX_DEBIAN)
        assert "apt" in instructions
        assert "ffmpeg" in instructions

    def test_redhat_instructions(self):
        """Test Red Hat installation instructions."""
        instructions = get_installation_instructions(OSType.LINUX_REDHAT)
        assert "dnf" in instructions
        assert "ffmpeg" in instructions

    def test_arch_instructions(self):
        """Test Arch installation instructions."""
        instructions = get_installation_instructions(OSType.LINUX_ARCH)
        assert "pacman" in instructions
        assert "ffmpeg" in instructions

    def test_macos_instructions(self):
        """Test macOS installation instructions."""
        instructions = get_installation_instructions(OSType.MACOS)
        assert "brew" in instructions
        assert "ffmpeg" in instructions

    def test_windows_instructions(self):
        """Test Windows installation instructions."""
        instructions = get_installation_instructions(OSType.WINDOWS)
        assert "choco" in instructions or "winget" in instructions
        assert "ffmpeg" in instructions

    def test_unknown_instructions(self):
        """Test unknown OS installation instructions."""
        instructions = get_installation_instructions(OSType.UNKNOWN)
        assert "ffmpeg.org" in instructions


class TestFormatDependencyCheck:
    """Tests for the format_dependency_check function."""

    def test_format_all_found(self):
        """Test formatting when all dependencies found."""
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(
                name="ffmpeg",
                found=True,
                path="/usr/bin/ffmpeg",
                version="ffmpeg version 6.0",
            ),
            ffprobe=DependencyStatus(
                name="ffprobe",
                found=True,
                path="/usr/bin/ffprobe",
                version="ffprobe version 6.0",
            ),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )

        output = format_dependency_check(result)

        assert "ffmpeg" in output
        assert "ffprobe" in output
        assert "All dependencies satisfied" in output
        assert "Ubuntu 24.04" in output

    def test_format_missing_dependencies(self):
        """Test formatting when dependencies missing."""
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(name="ffmpeg", found=False),
            ffprobe=DependencyStatus(name="ffprobe", found=False),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )

        output = format_dependency_check(result)

        assert "NOT FOUND" in output
        assert "INSTALLATION INSTRUCTIONS" in output
        assert "apt" in output  # Debian instructions

    def test_format_truncates_long_version(self):
        """Test that long version strings are truncated."""
        long_version = "x" * 100
        result = DependencyCheckResult(
            ffmpeg=DependencyStatus(
                name="ffmpeg", found=True, path="/usr/bin/ffmpeg", version=long_version
            ),
            ffprobe=DependencyStatus(
                name="ffprobe", found=True, path="/usr/bin/ffprobe"
            ),
            os_type=OSType.LINUX_DEBIAN,
            os_name="Ubuntu 24.04",
        )

        output = format_dependency_check(result)

        # Version should be truncated
        assert long_version not in output
        assert "..." in output


class TestCheckDependencies:
    """Tests for the check_dependencies function."""

    @patch("m4b_splitter.dependencies.detect_os")
    @patch("m4b_splitter.dependencies.check_dependency")
    def test_check_dependencies_returns_result(self, mock_check, mock_detect):
        """Test that check_dependencies returns proper result."""
        mock_detect.return_value = (OSType.LINUX_DEBIAN, "Ubuntu 24.04")
        mock_check.side_effect = [
            DependencyStatus(name="ffmpeg", found=True, path="/usr/bin/ffmpeg"),
            DependencyStatus(name="ffprobe", found=True, path="/usr/bin/ffprobe"),
        ]

        result = check_dependencies()

        assert isinstance(result, DependencyCheckResult)
        assert result.os_type == OSType.LINUX_DEBIAN
        assert result.os_name == "Ubuntu 24.04"
