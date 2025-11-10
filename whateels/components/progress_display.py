"""
Progress Display Component for WhatEELS Application

Provides a complete, ready-to-use progress display widget.
Can be embedded directly in any view/layout.

Features:
- Percentage-based progress bar
- Status messages with color coding
- Loading spinner
- Stage-based progress tracking
"""

import panel as pn
from typing import Optional, Dict


class ProgressDisplay(pn.Column):
    """
    Standalone progress display component that can be embedded in any layout.
    
    Combines progress bar, status message, and optional spinner into a single
    viewable component. Easier to use than mixin for simple cases.
    
    Example:
        progress = ProgressDisplay(name="File Upload")
        layout = pn.Column(
            progress,
            other_content
        )
        
        # Later, update progress:
        progress.update(25, "Reading file...")
        progress.update(50, "Processing data...")
        progress.update(100, "Complete!", 'success')
    """
    
    def __init__(self, name: str = "Progress", width: Optional[int] = 400):
        """
        Initialize the progress display.
        
        Args:
            name: Title for the progress indicator
            width: Width of components in pixels. None for responsive width.
        """
        self._display_name = name
        self._display_width = width
        
        # Progress bar
        self._progress_bar = pn.indicators.Progress(
            name=self._display_name,
            value=0,
            max=100,
            visible=False,
            width=self._display_width,
            sizing_mode='stretch_width' if self._display_width is None else None
        )
        
        # Status text
        self._status_text = pn.pane.Markdown(
            f'**{self._display_name}**: Ready',
            visible=False,
            width=self._display_width,
            styles=self._get_color_styles('info')
        )
        
        # Loading spinner (optional, for indeterminate progress)
        self._spinner = pn.indicators.LoadingSpinner(
            value=True,
            width=30,
            height=30,
            visible=False
        )
        
        # Spinner + text row
        self._spinner_row = pn.Row(
            self._spinner,
            pn.pane.Str(" Loading...", width=150),
            visible=False,
            sizing_mode='stretch_width' if self._display_width is None else None
        )
        
        # Initialize parent Column with components
        super().__init__(
            self._progress_bar,
            self._status_text,
            self._spinner_row,
            visible=False,
            sizing_mode='stretch_width'
        )
    
    @staticmethod
    def _get_color_styles(level: str) -> Dict[str, str]:
        """Get style dictionary for message level."""
        colors = {
            'info': '#e3f2fd',      # Light blue
            'success': '#e8f5e9',   # Light green
            'warning': '#fff3e0',   # Light orange
            'error': '#ffebee'      # Light red
        }
        
        return {
            'background': colors.get(level, colors['info']),
            'padding': '10px',
            'border-radius': '5px',
            'font-size': '14px'
        }
    
    def set_visible(self, visible: bool) -> None:
        """
        Set visibility of progress display.
        
        Args:
            visible: True to show, False to hide
        """
        self.visible = visible
    
    def is_visible(self) -> bool:
        """Check if progress display is visible."""
        return self.visible
    
    def _show(self) -> None:
        """Internal: Make the progress display visible."""
        self.visible = True
    
    def _hide(self) -> None:
        """Internal: Hide the progress display."""
        self.visible = False
        self.reset()
    
    def update(
        self, 
        value: int, 
        message: Optional[str] = None, 
        level: str = 'info', 
        max_value: int = 100
    ) -> None:
        """
        Update progress bar and status message.
        
        Args:
            value: Current progress value (0-max_value)
            message: Status message to display
            level: Message level - 'info', 'success', 'warning', 'error'
            max_value: Maximum progress value (default: 100)
            
        Example:
            progress.update(50, "Processing...", 'info')
            progress.update(100, "Complete!", 'success')
        """
        self._show()
        
        # Update progress bar
        self._progress_bar.max = max_value
        self._progress_bar.value = value
        self._progress_bar.visible = True
        
        # Update status message
        if message:
            self._status_text.object = f'**{self._display_name}**: {message}'
            self._status_text.styles = self._get_color_styles(level)
            self._status_text.visible = True
        
        # Hide spinner when showing progress
        self._spinner_row.visible = False
    
    def show_spinner(self, message: str = "Loading...") -> None:
        """
        Show indeterminate loading spinner.
        
        Use when you can't determine exact progress percentage.
        
        Args:
            message: Message to display next to spinner
        """
        self._show()
        
        # Update spinner message in row (recreate for safety)
        self._spinner_row.clear()
        self._spinner_row.append(self._spinner)
        self._spinner_row.append(pn.pane.Str(f" {message}", width=150))
        
        # Hide progress bar, show spinner
        self._progress_bar.visible = False
        self._spinner_row.visible = True
    
    def hide_spinner(self) -> None:
        """Hide the loading spinner."""
        self._spinner_row.visible = False
    
    def reset(self) -> None:
        """Reset progress to initial state."""
        self._progress_bar.value = 0
        self._progress_bar.visible = False
        self._status_text.object = f'**{self._display_name}**: Ready'
        self._status_text.visible = False
        self._spinner_row.visible = False
    
    def set_stages(self, stages: Dict[int, str]) -> None:
        """
        Set named stages for multi-stage operations.
        
        Args:
            stages: Dictionary mapping progress values to stage names
            
        Example:
            progress.set_stages({
                10: "Validating file",
                30: "Reading data",
                60: "Processing",
                90: "Finalizing",
                100: "Complete"
            })
            
            progress.update_stage(10)  # "Validating file"
        """
        self._stages = stages
    
    def update_stage(self, stage_value: int, level: str = 'info') -> None:
        """
        Update to a named stage.
        
        Args:
            stage_value: Key from stages dictionary
            level: Message level
            
        Example:
            progress.update(stage_value)  # Updates to "Reading data"
        """
        if hasattr(self, '_stages') and stage_value in self._stages:
            message = self._stages[stage_value]
            self.update(stage_value, message, level)
        else:
            self.update(stage_value, level=level)
    
    def completion(self, message: str = "Complete!") -> None:
        """
        Mark operation as complete with success state.
        
        Args:
            message: Completion message (default: "Complete!")
        """
        self.update(100, message, 'success')
    
    def error(self, message: str) -> None:
        """
        Mark operation as failed with error message.
        
        Args:
            message: Error message to display
        """
        self._progress_bar.visible = False
        self._status_text.object = f'**{self._display_name}**: {message}'
        self._status_text.styles = self._get_color_styles('error')
        self._status_text.visible = True
        self._show()
