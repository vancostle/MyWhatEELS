import panel as pn
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd

from whateels.components import ResizableColumns
from whateels.components.splitjs import SplitJs

class DemoPageView:
    
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model) -> None:
        self._left_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._right_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        
        data = pd.DataFrame([
            ('Monday', 7), ('Tuesday', 4), ('Wednesday', 9), ('Thursday', 4),
            ('Friday', 4), ('Saturday', 4), ('Sunday', 4)], columns=['Day', 'Orders']
        )

        fig_responsive = px.line(data, x="Day", y="Orders")
        fig_responsive.update_traces(mode="lines+markers", marker=dict(size=10), line=dict(width=4))

        left_plot_pane = pn.pane.Plotly(
            fig_responsive,
            sizing_mode=self._STRETCH_BOTH,
            config={"responsive": True},
            margin=0
        )
        
        right_fig_responsive = px.line(data, x="Day", y="Orders")
        right_fig_responsive.update_traces(mode="lines+markers", marker=dict(size=10), line=dict(width=4))
        
        right_plot_pane = pn.pane.Plotly(
            right_fig_responsive,
            sizing_mode=self._STRETCH_BOTH,
            config={"responsive": True},
            margin=0
        )        
        splitjswrapper = SplitJs(
            left_column=pn.Column(
                left_plot_pane,
                sizing_mode=self._STRETCH_BOTH,
            ),
            right_column=pn.Column(
                right_plot_pane,
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
    