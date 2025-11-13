"""Demo View - Right sidebar layout for controls."""

import panel as pn


class DemoRightSidebarLayout(pn.Column):
    """Right sidebar with controls for demo progress display."""
    
    def __init__(self):
        """Initialize right sidebar with duration input and run button."""
        # Load duration slider (0.5 to 30 seconds)
        self.duration_slider = pn.widgets.FloatSlider(
            name='Load Duration (seconds)',
            start=0.5,
            end=30,
            step=0.5,
            value=5,
            width=250
        )
        
        # Run button
        self.run_button = pn.widgets.Button(
            name='▶ Start Demo',
            button_type='primary',
            width=250
        )
        
        super().__init__(
            pn.pane.Markdown("## Demo Controls", styles={'padding': '10px'}),
            self.duration_slider,
            pn.pane.Markdown("", height=20),  # Spacer
            self.run_button,
            sizing_mode='stretch_width',
            styles={'padding': '20px', 'overflow_y': 'auto'}
        )
