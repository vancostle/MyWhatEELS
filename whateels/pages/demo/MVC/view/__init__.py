import panel as pn
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np

from whateels.components import ResizableColumns
from whateels.components.splitjs import SplitJs

class DemoPageView:
    
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model) -> None:
        self._left_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._right_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        
        # Simple heatmap (like paneA in spectrum_image_plot)
        ny, nx = 50, 50
        m_image = np.random.rand(ny, nx) * 100
        
        figA = go.Figure(data=[go.Heatmap(
            z=m_image,
            colorscale="Greys_r",
            showscale=False
        )])
        figA.update_layout(
            margin=dict(l=16, r=16, t=50, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        figA.update_yaxes(autorange="reversed", showgrid=False, zeroline=False, showticklabels=False)
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
        
        self.paneA = pn.pane.Plotly(
            figA,
            config={"responsive": True},
            sizing_mode='stretch_both',
            margin=0
        )
        
        # Simple line chart (like paneB in spectrum_image_plot)
        energy = np.linspace(0, 100, 200)
        spectrum = np.random.rand(200) * 1000
        
        figB = go.Figure(data=[go.Scatter(
            x=energy,
            y=spectrum,
            mode="lines"
        )])
        figB.update_layout(
            title="Spectrum",
            margin=dict(l=16, r=16, t=48, b=16),
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (a.u.)"
        )
        
        self.paneB = pn.pane.Plotly(
            figB,
            config={"responsive": True},
            sizing_mode='stretch_both',
            margin=0
        )
        
        splitjswrapper = SplitJs(
            left_column=pn.Column(
                self.paneA,
                sizing_mode=self._STRETCH_BOTH,
            ),
            right_column=pn.Column(
                self.paneB,
                sizing_mode=self._STRETCH_BOTH,
            ),
            sizing_mode=self._STRETCH_BOTH,
        )
        
        self._main = pn.Column(
            splitjswrapper,
            sizing_mode=self._STRETCH_BOTH
        )
        
    @property
    def main(self) -> pn.Column:
        return self._main
    
    @property
    def left_sidebar(self) -> pn.Column:
        return self._left_sidebar
    
    @property
    def right_sidebar(self) -> pn.Column:
        return self._right_sidebar
    