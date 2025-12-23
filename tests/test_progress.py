"""Unit tests for the progress module."""

import pytest
from pathlib import Path
from io import StringIO

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m4b_splitter.progress import (
    ProgressStep,
    ProgressUpdate,
    ProgressCallback,
    ConsoleProgress,
    SilentProgress,
    ProgressTracker,
)


class TestProgressStep:
    """Tests for the ProgressStep enum."""
    
    def test_all_steps_exist(self):
        """Test that all expected progress steps are defined."""
        assert ProgressStep.VALIDATING
        assert ProgressStep.EXTRACTING_METADATA
        assert ProgressStep.EXTRACTING_CHAPTERS
        assert ProgressStep.PLANNING_SPLITS
        assert ProgressStep.EXTRACTING_COVER
        assert ProgressStep.SPLITTING_AUDIO
        assert ProgressStep.WRITING_METADATA
        assert ProgressStep.FINALIZING


class TestProgressUpdate:
    """Tests for the ProgressUpdate dataclass."""
    
    def test_basic_update(self):
        """Test creating a basic progress update."""
        update = ProgressUpdate(
            step=ProgressStep.VALIDATING,
            message="Validating file..."
        )
        assert update.step == ProgressStep.VALIDATING
        assert update.message == "Validating file..."
        assert update.current == 0
        assert update.total == 0
        assert update.detail is None
    
    def test_update_with_progress(self):
        """Test creating an update with progress information."""
        update = ProgressUpdate(
            step=ProgressStep.SPLITTING_AUDIO,
            message="Splitting",
            current=5,
            total=10,
            detail="Processing chapter 5"
        )
        assert update.current == 5
        assert update.total == 10
        assert update.detail == "Processing chapter 5"
    
    def test_percentage_calculation(self):
        """Test percentage calculation."""
        update = ProgressUpdate(
            step=ProgressStep.SPLITTING_AUDIO,
            message="Test",
            current=25,
            total=100
        )
        assert update.percentage == 25.0
    
    def test_percentage_half(self):
        """Test percentage at 50%."""
        update = ProgressUpdate(
            step=ProgressStep.SPLITTING_AUDIO,
            message="Test",
            current=5,
            total=10
        )
        assert update.percentage == 50.0
    
    def test_percentage_complete(self):
        """Test percentage at 100%."""
        update = ProgressUpdate(
            step=ProgressStep.SPLITTING_AUDIO,
            message="Test",
            current=10,
            total=10
        )
        assert update.percentage == 100.0
    
    def test_percentage_zero_total(self):
        """Test percentage with zero total."""
        update = ProgressUpdate(
            step=ProgressStep.VALIDATING,
            message="Test",
            current=0,
            total=0
        )
        assert update.percentage == 0.0


class TestConsoleProgress:
    """Tests for the ConsoleProgress class."""
    
    def test_console_progress_creation(self):
        """Test creating a console progress instance."""
        output = StringIO()
        progress = ConsoleProgress(output=output)
        assert progress.output == output
        assert progress.show_progress_bar
        assert progress.bar_width == 40
    
    def test_console_progress_custom_width(self):
        """Test creating console progress with custom bar width."""
        progress = ConsoleProgress(bar_width=20)
        assert progress.bar_width == 20
    
    def test_console_progress_no_bar(self):
        """Test creating console progress without progress bar."""
        progress = ConsoleProgress(show_progress_bar=False)
        assert not progress.show_progress_bar
    
    def test_on_progress_simple(self):
        """Test on_progress with simple message."""
        output = StringIO()
        progress = ConsoleProgress(output=output)
        
        update = ProgressUpdate(
            step=ProgressStep.VALIDATING,
            message="Checking file"
        )
        progress.on_progress(update)
        
        result = output.getvalue()
        assert "Validating" in result
        assert "Checking file" in result
    
    def test_on_progress_with_bar(self):
        """Test on_progress with progress bar."""
        output = StringIO()
        progress = ConsoleProgress(output=output)
        
        update = ProgressUpdate(
            step=ProgressStep.SPLITTING_AUDIO,
            message="Processing",
            current=5,
            total=10
        )
        progress.on_progress(update)
        
        result = output.getvalue()
        assert "5/10" in result
        assert "50" in result  # percentage
    
    def test_on_complete_success(self):
        """Test on_complete with success."""
        output = StringIO()
        progress = ConsoleProgress(output=output)
        
        progress.on_complete(True, "All done!")
        
        result = output.getvalue()
        assert "SUCCESS" in result
        assert "All done!" in result
        assert "✓" in result
    
    def test_on_complete_failure(self):
        """Test on_complete with failure."""
        output = StringIO()
        progress = ConsoleProgress(output=output)
        
        progress.on_complete(False, "Something failed")
        
        result = output.getvalue()
        assert "FAILED" in result
        assert "Something failed" in result
        assert "✗" in result
    
    def test_step_names_defined(self):
        """Test that all steps have names defined."""
        for step in ProgressStep:
            assert step in ConsoleProgress.STEP_NAMES
    
    def test_make_progress_bar_empty(self):
        """Test progress bar at 0%."""
        progress = ConsoleProgress(bar_width=10)
        bar = progress._make_progress_bar(0, 10)
        
        assert "[" in bar
        assert "]" in bar
        assert "0.0%" in bar
    
    def test_make_progress_bar_full(self):
        """Test progress bar at 100%."""
        progress = ConsoleProgress(bar_width=10)
        bar = progress._make_progress_bar(10, 10)
        
        assert "100.0%" in bar
        assert "█" in bar


class TestSilentProgress:
    """Tests for the SilentProgress class."""
    
    def test_silent_progress_does_nothing(self):
        """Test that silent progress produces no output."""
        progress = SilentProgress()
        
        # None of these should raise or produce output
        update = ProgressUpdate(
            step=ProgressStep.VALIDATING,
            message="Test"
        )
        progress.on_progress(update)
        progress.on_complete(True, "Done")
        progress.on_error("Error")
    
    def test_is_progress_callback(self):
        """Test that SilentProgress is a ProgressCallback."""
        progress = SilentProgress()
        assert isinstance(progress, ProgressCallback)


class TestProgressTracker:
    """Tests for the ProgressTracker class."""
    
    def test_tracker_creation(self):
        """Test creating a progress tracker."""
        tracker = ProgressTracker()
        assert tracker._callbacks == []
    
    def test_add_callback(self):
        """Test adding a callback."""
        tracker = ProgressTracker()
        callback = SilentProgress()
        
        tracker.add_callback(callback)
        
        assert callback in tracker._callbacks
    
    def test_remove_callback(self):
        """Test removing a callback."""
        tracker = ProgressTracker()
        callback = SilentProgress()
        
        tracker.add_callback(callback)
        tracker.remove_callback(callback)
        
        assert callback not in tracker._callbacks
    
    def test_update_notifies_callbacks(self):
        """Test that update notifies all callbacks."""
        tracker = ProgressTracker()
        
        # Create a mock callback
        received_updates = []
        
        class MockCallback(ProgressCallback):
            def on_progress(self, update):
                received_updates.append(update)
            def on_complete(self, success, message):
                pass
            def on_error(self, error):
                pass
        
        callback = MockCallback()
        tracker.add_callback(callback)
        
        tracker.update(
            step=ProgressStep.VALIDATING,
            message="Test message"
        )
        
        assert len(received_updates) == 1
        assert received_updates[0].message == "Test message"
    
    def test_complete_notifies_callbacks(self):
        """Test that complete notifies all callbacks."""
        tracker = ProgressTracker()
        
        completions = []
        
        class MockCallback(ProgressCallback):
            def on_progress(self, update):
                pass
            def on_complete(self, success, message):
                completions.append((success, message))
            def on_error(self, error):
                pass
        
        callback = MockCallback()
        tracker.add_callback(callback)
        
        tracker.complete(True, "All done")
        
        assert len(completions) == 1
        assert completions[0] == (True, "All done")
    
    def test_error_notifies_callbacks(self):
        """Test that error notifies all callbacks."""
        tracker = ProgressTracker()
        
        errors = []
        
        class MockCallback(ProgressCallback):
            def on_progress(self, update):
                pass
            def on_complete(self, success, message):
                pass
            def on_error(self, error):
                errors.append(error)
        
        callback = MockCallback()
        tracker.add_callback(callback)
        
        tracker.error("Something went wrong")
        
        assert len(errors) == 1
        assert errors[0] == "Something went wrong"
    
    def test_multiple_callbacks(self):
        """Test tracker with multiple callbacks."""
        tracker = ProgressTracker()
        
        count = {"updates": 0}
        
        class CountingCallback(ProgressCallback):
            def on_progress(self, update):
                count["updates"] += 1
            def on_complete(self, success, message):
                pass
            def on_error(self, error):
                pass
        
        tracker.add_callback(CountingCallback())
        tracker.add_callback(CountingCallback())
        tracker.add_callback(CountingCallback())
        
        tracker.update(ProgressStep.VALIDATING, "Test")
        
        # All 3 callbacks should be notified
        assert count["updates"] == 3
