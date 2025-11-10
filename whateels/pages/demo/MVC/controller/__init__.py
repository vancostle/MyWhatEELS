"""Demo Controller - Controller for demo page."""

import time
import threading
from whateels.components import ProgressDisplay
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..model import DemoModel
    from ..view import DemoView


class DemoController:
    """Controller for demo progress display page."""
    
    def __init__(self, model: "DemoModel", view: "DemoView"):
        """Initialize demo controller."""
        self._model = model
        self._view = view
        
        # Progress display
        self._progress_display = ProgressDisplay(name="Demo")
        
        # Show initial progress display
        self._view.main.update(self._progress_display)
        
        # Setup button handler
        self._view.right_sidebar.run_button.on_click(self._on_run_demo)
    
    def _on_run_demo(self, event):
        """Handle run button click."""
        duration = self._view.right_sidebar.duration_slider.value
        
        # Disable button during run
        self._view.right_sidebar.run_button.disabled = True
        
        # Run demo in background thread
        thread = threading.Thread(target=self._run_demo, args=(duration,), daemon=True)
        thread.start()
    
    def _run_demo(self, duration: float):
        """Run the demo with simulated loading."""
        try:
            # Reset and show spinner
            self._progress_display.reset()
            self._progress_display.visible = True
            self._progress_display.show_spinner(f"Demo loading for {duration} seconds...")
            
            # Simulate multi-stage loading
            stages = [
                (0.2 * duration, 25, "Preparing data..."),
                (0.4 * duration, 50, "Processing..."),
                (0.6 * duration, 75, "Finalizing..."),
                (0.8 * duration, 90, "Almost done..."),
            ]
            
            start_time = time.time()
            
            for wait_until, progress, message in stages:
                # Wait until this stage's time
                while time.time() - start_time < wait_until:
                    time.sleep(0.1)
                
                # Update progress
                self._progress_display.update(progress, message, level='info')
            
            # Wait for remaining time
            while time.time() - start_time < duration:
                time.sleep(0.1)
            
            # Mark complete
            self._progress_display.completion("Demo complete!")
            
            # Show completion for 2 seconds then restore placeholder
            time.sleep(2)
            self._view.main.update(self._progress_display)
            
        except Exception as e:
            print(f"Error in demo: {e}")
            self._progress_display.error(f"Demo failed: {str(e)}")
        finally:
            # Re-enable button
            self._view.right_sidebar.run_button.disabled = False
