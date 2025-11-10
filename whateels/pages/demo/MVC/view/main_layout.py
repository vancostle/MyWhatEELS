"""Demo View - Main layout for demo page."""

import panel as pn


class DemoMainLayout(pn.Column):
    """Main layout for demo progress display."""
    
    def __init__(self):
        """Initialize main layout with progress display placeholder."""
        super().__init__(
            pn.pane.Markdown(
                "**Progress display will appear here**",
                styles={'padding': '40px', 'text-align': 'center'}
            ),
            sizing_mode='stretch_both'
        )
    
    def update(self, component):
        """Update the main layout with a new component."""
        self.clear()
        self.append(component)
