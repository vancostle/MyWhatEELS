"""
Quick Test: Progress Components Demo

Run this to verify progress components work correctly.
"""

import panel as pn
import time
import threading

# Enable Panel extensions
pn.extension('plotly')

from whateels.components import ProgressDisplay, ProgressTrackerMixin
from whateels.base.mvc import BaseView


class SimpleProgressView(BaseView, ProgressTrackerMixin):
    """Simple view demonstrating ProgressTrackerMixin usage."""
    
    def __init__(self, model=None):
        # Initialize without model for demo purposes
        self.model = model
        self._init_progress_components()
        self.main = self._create_layout()
    
    def _create_layout(self):
        """Create the view layout with mixin progress components."""
        duration_input = pn.widgets.FloatSlider(
            name="Duration (seconds)", 
            start=0.5, 
            end=10, 
            step=0.5, 
            value=2
        )
        
        def run_mixin_progress():
            total_duration = duration_input.value if duration_input.value is not None else 2.0
            steps = [20, 40, 60, 80, 100]
            messages = [
                "Initializing...",
                "Loading data...",
                "Processing...",
                "Finalizing...",
                "Complete!"
            ]
            
            def run():
                for step, msg in zip(steps, messages):
                    time.sleep(total_duration / len(steps))
                    level = 'success' if step == 100 else 'info'
                    self.update_progress(step, msg, max_value=100)
                    self.update_progress_message(msg, level=level)
            
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
        
        button = pn.widgets.Button(name="Start Operation", button_type='success')
        button.on_click(lambda event: run_mixin_progress())
        
        layout = pn.Column(
            pn.pane.Markdown("# Demo 5: ProgressTrackerMixin (Integrated into View)"),
            pn.pane.Markdown("This demo shows ProgressTrackerMixin used in a View class."),
            duration_input,
            button,
            self.progress_container,
            sizing_mode='stretch_width'
        )
        
        return layout


def demo_tracker_mixin():
    """Demo 5: ProgressTrackerMixin integrated in a View"""
    view = SimpleProgressView()
    return view.main


def demo_progress_display():
    """Demo 1: Standalone ProgressDisplay"""
    
    progress = ProgressDisplay(name="File Upload")
    duration_input = pn.widgets.FloatSlider(
        name="Duration (seconds)", 
        start=0.5, 
        end=10, 
        step=0.5, 
        value=2
    )
    
    def simulate_upload():
        total_duration = float(duration_input.value) if duration_input.value is not None and isinstance(duration_input.value, (int, float, str)) else 2.0
        steps = [10, 25, 50, 75, 100]
        messages = [
            "Validating file...",
            "Reading DM data...",
            "Processing arrays...",
            "Creating visualization...",
            "Complete!"
        ]
        
        def run_progress():
            for i, (step, msg) in enumerate(zip(steps, messages)):
                time.sleep(total_duration / len(steps))
                level = 'success' if step == 100 else 'info'
                progress.update(step, msg, level=level)
        
        # Run in background thread so UI doesn't freeze
        thread = threading.Thread(target=run_progress, daemon=True)
        thread.start()
    
    button = pn.widgets.Button(name="Start Upload", button_type='primary')
    button.on_click(lambda event: simulate_upload())
    
    layout = pn.Column(
        pn.pane.Markdown("# Demo 1: ProgressDisplay Component"),
        pn.pane.Markdown("Set duration and click the button to simulate file upload with progress."),
        duration_input,
        button,
        progress,
        sizing_mode='stretch_width'
    )
    
    return layout


def demo_progress_with_stages():
    """Demo 2: ProgressDisplay with Stages"""
    
    progress = ProgressDisplay(name="Data Processing")
    duration_input = pn.widgets.FloatSlider(
        name="Duration (seconds)", 
        start=0.5, 
        end=10, 
        step=0.5, 
        value=2
    )
    
    progress.set_stages({
        10: "Validating file",
        30: "Reading data",
        60: "Processing",
        90: "Finalizing",
        100: "Complete"
    })
    
    def run_stages():
        total_duration = float(duration_input.value) if duration_input.value is not None and isinstance(duration_input.value, (int, float, str)) else 2.0
        stages = [10, 30, 60, 90, 100]
        
        def run_progress():
            for stage in stages:
                time.sleep(total_duration / len(stages))
                level = 'success' if stage == 100 else 'info'
                progress.update_stage(stage, level=level)
        
        # Run in background thread so UI doesn't freeze
        thread = threading.Thread(target=run_progress, daemon=True)
        thread.start()
    
    button = pn.widgets.Button(name="Run Stages", button_type='success')
    button.on_click(lambda event: run_stages())
    
    layout = pn.Column(
        pn.pane.Markdown("# Demo 2: Progress with Stages"),
        pn.pane.Markdown("Set duration and click to run through predefined stages."),
        duration_input,
        button,
        progress,
        sizing_mode='stretch_width'
    )
    
    return layout


def demo_loading_spinner():
    """Demo 3: Loading Spinner"""
    
    progress = ProgressDisplay(name="Processing")
    
    def show_spinner():
        progress.show_spinner("Connecting to server...")
    
    def show_progress():
        progress.update(50, "Processing...", 'info')
    
    button1 = pn.widgets.Button(name="Show Spinner", button_type='warning')
    button2 = pn.widgets.Button(name="Switch to Progress", button_type='primary')
    button1.on_click(lambda event: show_spinner())
    button2.on_click(lambda event: show_progress())
    
    layout = pn.Column(
        pn.pane.Markdown("# Demo 3: Loading Spinner"),
        pn.pane.Markdown("Demo spinner vs progress bar."),
        pn.Row(button1, button2),
        progress,
        sizing_mode='stretch_width'
    )
    
    return layout


def demo_status_levels():
    """Demo 4: Status Levels"""
    
    progress = ProgressDisplay(name="Operation")
    
    def show_info():
        progress.update(25, "Step in progress...", level='info')
    
    def show_warning():
        progress.update(50, "Potential issue detected", level='warning')
    
    def show_error():
        progress.error("Operation failed!")
    
    def show_success():
        progress.completion("Operation completed!")
    
    button_info = pn.widgets.Button(name="Info", button_type='light')
    button_warning = pn.widgets.Button(name="Warning", button_type='warning')
    button_error = pn.widgets.Button(name="Error", button_type='danger')
    button_success = pn.widgets.Button(name="Success", button_type='success')
    
    button_info.on_click(lambda event: show_info())
    button_warning.on_click(lambda event: show_warning())
    button_error.on_click(lambda event: show_error())
    button_success.on_click(lambda event: show_success())
    
    layout = pn.Column(
        pn.pane.Markdown("# Demo 4: Status Levels"),
        pn.pane.Markdown("Click buttons to see different status levels."),
        pn.Row(button_info, button_warning, button_error, button_success),
        progress,
        sizing_mode='stretch_width'
    )
    
    return layout


if __name__ == "__main__":
    # Run all demos
    template = pn.template.FastListTemplate(
        title="Progress Component Demos",
        main=[
            demo_progress_display(),
            pn.layout.Divider(),
            demo_progress_with_stages(),
            pn.layout.Divider(),
            demo_loading_spinner(),
            pn.layout.Divider(),
            demo_status_levels(),
            pn.layout.Divider(),
            demo_tracker_mixin(),
        ]
    )
    
    template.show(port=5007)
