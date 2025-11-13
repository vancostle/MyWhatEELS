"""
Progress Tracker Mixin for WhatEELS Application

Provides reusable progress tracking functionality with visual indicators.
Designed to be mixed into View classes for consistent progress display.

Features:
- Progress bar with percentage display
- Status message updates
- Loading spinner indicator
- Multi-stage progress tracking
- Automatic visibility management
"""

import panel as pn
from typing import Optional, Callable


class ProgressTrackerMixin:
    """
    Mixin class providing progress tracking capabilities for View classes.
    
    Provides methods to:
    - Show/hide progress bars with percentage updates
    - Display status messages with color coding
    - Show loading spinners
    - Track multi-stage operations
    
    Classes using this mixin should initialize progress components in their __init__.
    
    Example:
        class MyView(BaseView, ProgressTrackerMixin):
            def __init__(self, model):
                super().__init__(model)
                self._init_progress_components()  # Initialize mixin components
    """
    
    def _init_progress_components(self) -> None:
        """
        Initialize progress tracking components.
        
        Call this in your View's __init__ after super().__init__().
        Creates progress bar, status text, and loading spinner.
        """
        # Progress bar for percentage-based tracking
        self.progress_bar = pn.indicators.Progress(
            name='Progress',
            value=0,
            max=100,
            visible=False,
            width=400,
            sizing_mode='stretch_width'
        )
        
        # Status text for operation messages
        self.progress_status_text = pn.pane.Markdown(
            '**Status**: Ready',
            visible=False,
            width=400,
            styles={
                'background': '#e3f2fd',
                'padding': '10px',
                'border-radius': '5px',
                'font-size': '14px'
            }
        )
        
        # Loading spinner for indeterminate progress
        self.progress_spinner = pn.indicators.LoadingSpinner(
            value=True,
            width=30,
            height=30,
            visible=False
        )
        
        # Combined progress container (bar + status)
        self.progress_container = pn.Column(
            self.progress_bar,
            self.progress_status_text,
            visible=False,
            sizing_mode='stretch_width'
        )
    
    def show_progress(self, value: int, max_value: int = 100) -> None:
        """
        Update and show the progress bar.
        
        Args:
            value: Current progress value (0-100 or 0-max_value)
            max_value: Maximum progress value (default: 100)
            
        Example:
            self.show_progress(50, 100)  # 50%
        """
        if not hasattr(self, 'progress_bar'):
            raise RuntimeError("Progress components not initialized. Call _init_progress_components() first.")
        
        self.progress_bar.max = max_value
        self.progress_bar.value = value
        self.progress_bar.visible = True
        self.progress_container.visible = True
    
    def hide_progress(self) -> None:
        """
        Hide the progress bar and reset to zero.
        
        Call this when operation completes or is cancelled.
        """
        if not hasattr(self, 'progress_bar'):
            return
        
        self.progress_bar.visible = False
        self.progress_bar.value = 0
        self.progress_status_text.visible = False
        self.progress_container.visible = False
    
    def update_progress(self, value: int, message: Optional[str] = None, max_value: int = 100) -> None:
        """
        Update progress bar and optional status message.
        
        Combines show_progress() with status text update.
        
        Args:
            value: Current progress value
            message: Optional status message to display
            max_value: Maximum progress value (default: 100)
            
        Example:
            self.update_progress(25, "Reading file...", 100)
        """
        self.show_progress(value, max_value)
        
        if message:
            self.update_progress_message(message, 'info')
    
    def update_progress_message(self, message: str, level: str = 'info') -> None:
        """
        Update the progress status message with color coding.
        
        Args:
            message: Message text to display (markdown supported)
            level: Message level - 'info', 'success', 'warning', 'error' (default: 'info')
            
        Example:
            self.update_progress_message("Processing complete!", 'success')
        """
        if not hasattr(self, 'progress_status_text'):
            raise RuntimeError("Progress components not initialized. Call _init_progress_components() first.")
        
        # Color scheme for different message levels
        colors = {
            'info': '#e3f2fd',      # Light blue
            'success': '#e8f5e9',   # Light green
            'warning': '#fff3e0',   # Light orange
            'error': '#ffebee'      # Light red
        }
        
        self.progress_status_text.object = f'**Status**: {message}'
        self.progress_status_text.styles = {
            'background': colors.get(level, colors['info']),
            'padding': '10px',
            'border-radius': '5px',
            'font-size': '14px'
        }
        self.progress_status_text.visible = True
    
    def show_loading_spinner(self, show: bool = True) -> None:
        """
        Show or hide the loading spinner for indeterminate progress.
        
        Use this when you can't determine exact progress percentage.
        
        Args:
            show: True to show spinner, False to hide (default: True)
            
        Example:
            self.show_loading_spinner(True)   # Show
            self.show_loading_spinner(False)  # Hide
        """
        if not hasattr(self, 'progress_spinner'):
            raise RuntimeError("Progress components not initialized. Call _init_progress_components() first.")
        
        self.progress_spinner.visible = show
    
    def get_progress_container(self) -> pn.Column:
        """
        Get the progress container to add to your layout.
        
        Returns:
            Panel Column containing all progress components
            
        Example:
            layout = pn.Column(
                self.get_progress_container(),
                other_content
            )
        """
        if not hasattr(self, 'progress_container'):
            raise RuntimeError("Progress components not initialized. Call _init_progress_components() first.")
        
        return self.progress_container
    
    def reset_progress(self) -> None:
        """
        Reset progress to initial state (0%, not visible).
        
        Useful for resetting between operations.
        """
        self.hide_progress()
        if hasattr(self, 'progress_bar'):
            self.progress_bar.value = 0
        if hasattr(self, 'progress_status_text'):
            self.progress_status_text.object = '**Status**: Ready'
        if hasattr(self, 'progress_spinner'):
            self.progress_spinner.visible = False
