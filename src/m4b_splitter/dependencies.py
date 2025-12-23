"""FFmpeg dependency checking and installation guidance."""

import platform
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum, auto


class OSType(Enum):
    """Operating system types."""

    LINUX_DEBIAN = auto()  # Debian, Ubuntu, Mint, Pop!_OS
    LINUX_REDHAT = auto()  # RHEL, Fedora, CentOS, Rocky
    LINUX_ARCH = auto()  # Arch, Manjaro
    LINUX_SUSE = auto()  # openSUSE
    LINUX_ALPINE = auto()  # Alpine
    LINUX_OTHER = auto()  # Other Linux
    MACOS = auto()
    WINDOWS = auto()
    UNKNOWN = auto()


@dataclass
class DependencyStatus:
    """Status of a dependency check."""

    name: str
    found: bool
    path: str | None = None
    version: str | None = None


@dataclass
class DependencyCheckResult:
    """Result of checking all dependencies."""

    ffmpeg: DependencyStatus
    ffprobe: DependencyStatus
    os_type: OSType
    os_name: str

    @property
    def all_found(self) -> bool:
        """Check if all dependencies are found."""
        return self.ffmpeg.found and self.ffprobe.found

    @property
    def missing(self) -> list[str]:
        """Get list of missing dependencies."""
        missing = []
        if not self.ffmpeg.found:
            missing.append("ffmpeg")
        if not self.ffprobe.found:
            missing.append("ffprobe")
        return missing


def detect_os() -> tuple[OSType, str]:
    """
    Detect the operating system and distribution.

    Returns:
        Tuple of (OSType, human-readable name).
    """
    system = platform.system().lower()

    if system == "darwin":
        version = platform.mac_ver()[0]
        return OSType.MACOS, f"macOS {version}"

    elif system == "windows":
        version = platform.win32_ver()[0]
        return OSType.WINDOWS, f"Windows {version}"

    elif system == "linux":
        # Try to detect Linux distribution
        try:
            # Try /etc/os-release first (modern standard)
            with open("/etc/os-release") as f:
                os_release = {}
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        os_release[key] = value.strip('"')

                dist_id = os_release.get("ID", "").lower()
                dist_id_like = os_release.get("ID_LIKE", "").lower()
                dist_name = os_release.get("PRETTY_NAME", "Linux")

                # Check for Debian-based
                if dist_id in (
                    "debian",
                    "ubuntu",
                    "linuxmint",
                    "pop",
                    "elementary",
                    "zorin",
                    "kali",
                ):
                    return OSType.LINUX_DEBIAN, dist_name
                if "debian" in dist_id_like or "ubuntu" in dist_id_like:
                    return OSType.LINUX_DEBIAN, dist_name

                # Check for Red Hat-based
                if dist_id in ("fedora", "rhel", "centos", "rocky", "almalinux", "oracle"):
                    return OSType.LINUX_REDHAT, dist_name
                if "fedora" in dist_id_like or "rhel" in dist_id_like:
                    return OSType.LINUX_REDHAT, dist_name

                # Check for Arch-based
                if dist_id in ("arch", "manjaro", "endeavouros", "garuda"):
                    return OSType.LINUX_ARCH, dist_name
                if "arch" in dist_id_like:
                    return OSType.LINUX_ARCH, dist_name

                # Check for SUSE-based
                if dist_id in ("opensuse", "suse", "opensuse-leap", "opensuse-tumbleweed"):
                    return OSType.LINUX_SUSE, dist_name
                if "suse" in dist_id_like:
                    return OSType.LINUX_SUSE, dist_name

                # Check for Alpine
                if dist_id == "alpine":
                    return OSType.LINUX_ALPINE, dist_name

                return OSType.LINUX_OTHER, dist_name

        except FileNotFoundError:
            pass

        return OSType.LINUX_OTHER, "Linux"

    return OSType.UNKNOWN, platform.system()


def get_version(executable: str) -> str | None:
    """
    Get version string of an executable.

    Args:
        executable: Path to the executable.

    Returns:
        Version string or None if not found.
    """
    try:
        result = subprocess.run(
            [executable, "-version"], check=False, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Extract first line which usually contains version
            first_line = result.stdout.split("\n")[0]
            return first_line
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def check_dependency(name: str) -> DependencyStatus:
    """
    Check if a dependency is available.

    Args:
        name: Name of the executable to check.

    Returns:
        DependencyStatus with check results.
    """
    path = shutil.which(name)

    if path:
        version = get_version(path)
        return DependencyStatus(name=name, found=True, path=path, version=version)

    return DependencyStatus(name=name, found=False)


def check_dependencies() -> DependencyCheckResult:
    """
    Check all required dependencies.

    Returns:
        DependencyCheckResult with status of all dependencies.
    """
    os_type, os_name = detect_os()

    return DependencyCheckResult(
        ffmpeg=check_dependency("ffmpeg"),
        ffprobe=check_dependency("ffprobe"),
        os_type=os_type,
        os_name=os_name,
    )


def get_installation_instructions(os_type: OSType) -> str:
    """
    Get installation instructions for the detected OS.

    Args:
        os_type: The detected operating system type.

    Returns:
        Installation instructions as a string.
    """
    instructions = {
        OSType.LINUX_DEBIAN: """
  For Debian/Ubuntu/Mint, run:
    sudo apt update
    sudo apt install ffmpeg

  For the latest version, you can use a PPA:
    sudo add-apt-repository ppa:savoury1/ffmpeg4
    sudo apt update
    sudo apt install ffmpeg""",
        OSType.LINUX_REDHAT: """
  For Fedora, run:
    sudo dnf install ffmpeg ffmpeg-devel

  For RHEL/CentOS/Rocky, enable RPM Fusion first:
    sudo dnf install epel-release
    sudo dnf install --nogpgcheck https://mirrors.rpmfusion.org/free/el/rpmfusion-free-release-$(rpm -E %rhel).noarch.rpm
    sudo dnf install ffmpeg""",
        OSType.LINUX_ARCH: """
  For Arch/Manjaro, run:
    sudo pacman -S ffmpeg""",
        OSType.LINUX_SUSE: """
  For openSUSE, run:
    sudo zypper install ffmpeg

  Or from Packman repository for full codec support:
    sudo zypper addrepo -cfp 90 'https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Tumbleweed/' packman
    sudo zypper refresh
    sudo zypper install --from packman ffmpeg""",
        OSType.LINUX_ALPINE: """
  For Alpine Linux, run:
    sudo apk add ffmpeg""",
        OSType.LINUX_OTHER: """
  For most Linux distributions, ffmpeg is available in the package manager.
  Try one of these commands:
    sudo apt install ffmpeg      # Debian-based
    sudo dnf install ffmpeg      # Fedora/RHEL
    sudo pacman -S ffmpeg        # Arch-based
    sudo zypper install ffmpeg   # openSUSE

  Or build from source:
    https://ffmpeg.org/download.html#build-linux""",
        OSType.MACOS: """
  For macOS, the easiest way is using Homebrew:
    brew install ffmpeg

  If you don't have Homebrew installed:
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    brew install ffmpeg

  Alternatively, use MacPorts:
    sudo port install ffmpeg""",
        OSType.WINDOWS: """
  For Windows, you have several options:

  Option 1 - Using Chocolatey (recommended):
    choco install ffmpeg

  Option 2 - Using winget:
    winget install ffmpeg

  Option 3 - Using Scoop:
    scoop install ffmpeg

  Option 4 - Manual installation:
    1. Download from: https://ffmpeg.org/download.html#build-windows
       (or https://www.gyan.dev/ffmpeg/builds/)
    2. Extract the archive
    3. Add the 'bin' folder to your PATH environment variable

  After installation, restart your terminal/command prompt.""",
        OSType.UNKNOWN: """
  Please visit https://ffmpeg.org/download.html for installation
  instructions for your operating system.

  FFmpeg is available for Windows, macOS, Linux, and BSD systems.""",
    }

    return instructions.get(os_type, instructions[OSType.UNKNOWN])


def format_dependency_check(result: DependencyCheckResult) -> str:
    """
    Format dependency check result as a human-readable string.

    Args:
        result: The dependency check result.

    Returns:
        Formatted string for display.
    """
    lines = []
    lines.append("=" * 60)
    lines.append("DEPENDENCY CHECK")
    lines.append("=" * 60)
    lines.append(f"\nOperating System: {result.os_name}")
    lines.append("")

    # FFmpeg status
    if result.ffmpeg.found:
        lines.append("✓ ffmpeg:  Found")
        lines.append(f"  Path:    {result.ffmpeg.path}")
        if result.ffmpeg.version:
            # Truncate long version strings
            version = result.ffmpeg.version
            if len(version) > 60:
                version = version[:57] + "..."
            lines.append(f"  Version: {version}")
    else:
        lines.append("✗ ffmpeg:  NOT FOUND")

    lines.append("")

    # FFprobe status
    if result.ffprobe.found:
        lines.append("✓ ffprobe: Found")
        lines.append(f"  Path:    {result.ffprobe.path}")
        if result.ffprobe.version:
            version = result.ffprobe.version
            if len(version) > 60:
                version = version[:57] + "..."
            lines.append(f"  Version: {version}")
    else:
        lines.append("✗ ffprobe: NOT FOUND")

    lines.append("")

    # Overall status and instructions
    if result.all_found:
        lines.append("Status: All dependencies satisfied ✓")
    else:
        lines.append(f"Status: Missing dependencies: {', '.join(result.missing)}")
        lines.append("")
        lines.append("INSTALLATION INSTRUCTIONS")
        lines.append("-" * 40)
        lines.append(get_installation_instructions(result.os_type))

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)


def ensure_dependencies() -> DependencyCheckResult:
    """
    Check dependencies and print status.

    This is a convenience function that checks dependencies,
    prints the result, and returns the check result.

    Returns:
        DependencyCheckResult with status of all dependencies.
    """
    result = check_dependencies()
    print(format_dependency_check(result))
    return result


def require_dependencies() -> None:
    """
    Check dependencies and raise an error if any are missing.

    Raises:
        RuntimeError: If ffmpeg or ffprobe is not found.
    """
    result = check_dependencies()

    if not result.all_found:
        error_msg = format_dependency_check(result)
        raise RuntimeError(
            f"Missing required dependencies: {', '.join(result.missing)}\n\n{error_msg}"
        )
