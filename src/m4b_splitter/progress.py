"""Progress tracking and display for M4B splitting operations."""

import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar, TextIO


class ProgressStep(Enum):
    """Steps in the M4B splitting process."""

    VALIDATING = auto()
    EXTRACTING_METADATA = auto()
    EXTRACTING_CHAPTERS = auto()
    PLANNING_SPLITS = auto()
    EXTRACTING_COVER = auto()
    SPLITTING_AUDIO = auto()
    WRITING_METADATA = auto()
    FINALIZING = auto()


@dataclass
class ProgressUpdate:
    """Represents a progress update."""

    step: ProgressStep
    message: str
    current: int = 0
    total: int = 0
    detail: str | None = None

    @property
    def percentage(self) -> float:
        """Get progress percentage."""
        if self.total == 0:
            return 0.0
        return (self.current / self.total) * 100


class ProgressCallback(ABC):
    """Abstract base class for progress callbacks."""

    @abstractmethod
    def on_progress(self, update: ProgressUpdate) -> None:
        """Called when progress is updated."""
        pass

    @abstractmethod
    def on_complete(self, success: bool, message: str) -> None:
        """Called when operation completes."""
        pass

    @abstractmethod
    def on_error(self, error: str) -> None:
        """Called when an error occurs."""
        pass


class ConsoleProgress(ProgressCallback):
    """Console-based progress display."""

    STEP_NAMES: ClassVar[dict[ProgressStep, str]] = {
        ProgressStep.VALIDATING: "Validating input file",
        ProgressStep.EXTRACTING_METADATA: "Extracting metadata",
        ProgressStep.EXTRACTING_CHAPTERS: "Extracting chapters",
        ProgressStep.PLANNING_SPLITS: "Planning splits",
        ProgressStep.EXTRACTING_COVER: "Extracting cover art",
        ProgressStep.SPLITTING_AUDIO: "Splitting audio",
        ProgressStep.WRITING_METADATA: "Writing metadata",
        ProgressStep.FINALIZING: "Finalizing",
    }

    def __init__(
        self,
        output: TextIO = sys.stdout,
        show_progress_bar: bool = True,
        bar_width: int = 40,
    ):
        """
        Initialize console progress display.

        Args:
            output: Output stream (default: stdout).
            show_progress_bar: Whether to show progress bars.
            bar_width: Width of progress bar in characters.
        """
        self.output = output
        self.show_progress_bar = show_progress_bar
        self.bar_width = bar_width
        self._current_step: ProgressStep | None = None

    def on_progress(self, update: ProgressUpdate) -> None:
        """Display progress update."""
        step_name = self.STEP_NAMES.get(update.step, str(update.step))

        # Print step header if step changed
        if update.step != self._current_step:
            self._current_step = update.step
            print(f"\n[{step_name}]", file=self.output)

        # Build progress line
        if update.total > 0 and self.show_progress_bar:
            bar = self._make_progress_bar(update.current, update.total)
            line = f"\r  {bar} {update.current}/{update.total}"
        else:
            line = f"  {update.message}"

        if update.detail:
            line += f" - {update.detail}"

        # Print with or without newline based on whether we have more progress
        if update.total > 0 and update.current < update.total:
            print(line, end="", file=self.output, flush=True)
        else:
            print(line, file=self.output, flush=True)

    def on_complete(self, success: bool, message: str) -> None:
        """Display completion message."""
        symbol = "✓" if success else "✗"
        status = "SUCCESS" if success else "FAILED"
        print(f"\n[{symbol}] {status}: {message}", file=self.output)

    def on_error(self, error: str) -> None:
        """Display error message."""
        print(f"\n[ERROR] {error}", file=sys.stderr)

    def _make_progress_bar(self, current: int, total: int) -> str:
        """Create a text progress bar."""
        if total == 0:
            return "[" + " " * self.bar_width + "]"

        filled = int((current / total) * self.bar_width)
        empty = self.bar_width - filled
        percentage = (current / total) * 100

        return f"[{'█' * filled}{'░' * empty}] {percentage:5.1f}%"


class SilentProgress(ProgressCallback):
    """Silent progress callback that doesn't output anything."""

    def on_progress(self, update: ProgressUpdate) -> None:
        pass

    def on_complete(self, success: bool, message: str) -> None:
        pass

    def on_error(self, error: str) -> None:
        pass


class ProgressTracker:
    """
    Tracks progress and notifies callbacks.

    This class manages progress tracking for the splitting operation,
    allowing multiple callbacks to be notified of progress updates.
    """

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self._callbacks: list[ProgressCallback] = []

    def add_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback."""
        self._callbacks.remove(callback)

    def update(
        self,
        step: ProgressStep,
        message: str,
        current: int = 0,
        total: int = 0,
        detail: str | None = None,
    ) -> None:
        """
        Send a progress update to all callbacks.

        Args:
            step: Current processing step.
            message: Progress message.
            current: Current progress count.
            total: Total items to process.
            detail: Optional detail message.
        """
        update = ProgressUpdate(
            step=step, message=message, current=current, total=total, detail=detail
        )
        for callback in self._callbacks:
            callback.on_progress(update)

    def complete(self, success: bool, message: str) -> None:
        """
        Signal completion to all callbacks.

        Args:
            success: Whether the operation was successful.
            message: Completion message.
        """
        for callback in self._callbacks:
            callback.on_complete(success, message)

    def error(self, error: str) -> None:
        """
        Signal an error to all callbacks.

        Args:
            error: Error message.
        """
        for callback in self._callbacks:
            callback.on_error(error)
