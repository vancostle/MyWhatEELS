import panel as pn
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd

from whateels.components import ResizableColumns, SplitJsWrapper
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
        # Don't set width/height in the layout - let autosize work
        # autosize=True is the default, so the plot will fit its container

        plot_pane = pn.pane.Plotly(
            fig_responsive,
            sizing_mode=self._STRETCH_BOTH,
            config={"responsive": True},
            styles={"border": "2px solid #34495e", "border-radius": "5px"}
        )
        
        left_column = pn.Column(
            # plot_pane,
            sizing_mode=self._STRETCH_BOTH,
            styles={"background-color": "#59b966"}
        )
        right_column = pn.Column(
            pn.pane.Markdown("## Additional Info\nThis is the right sidebar."),
            sizing_mode=self._STRETCH_BOTH,
            styles={"background-color": "#f39c12"}
        )
        
        resizable_columns = ResizableColumns(
            left_column=left_column,
            right_column=right_column,
            sizing_mode=self._STRETCH_BOTH
        )
        
        self._right_sidebar.append(
            resizable_columns
        )
        
        splitjswrapper = SplitJs(
            left_column=pn.Column(
                plot_pane,
                sizing_mode=self._STRETCH_BOTH,
                styles={'background-color': '#8e44ad'}
            ),
            right_column=pn.Column(
                pn.pane.Markdown("## Right Pane\nThis is the right pane content."),
                sizing_mode=self._STRETCH_BOTH,
                styles={'background-color': '#2980b9'}
            ),
            sizing_mode=self._STRETCH_BOTH,
            styles={'border': '2px solid #34495e', 'border-radius': '5px'} 
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
    