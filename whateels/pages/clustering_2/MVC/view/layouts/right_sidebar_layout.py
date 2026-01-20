import panel as pn

from whateels.components import SimpleDetails
from bokeh.models import Tooltip

class Clustering2RightSidebarLayout(pn.Column):
    
    def __init__(self):
                
        self._min_cut_signal = pn.widgets.FloatInput(
            name="Min Eloss",
            value=0.1,
            step=0.1,
            start=0.0,
            end=100.0,
            sizing_mode="stretch_width"
        )
        self._max_cut_signal = pn.widgets.FloatInput(
            name="Max Eloss",
            value=100.0,
            step=0.1,
            start=99.9,
            end=100.0,
            sizing_mode="stretch_width"
        )
        
        cut_signal_content = pn.Column(
            pn.Row(
                self._min_cut_signal,
                self._max_cut_signal,
                sizing_mode="stretch_width",
            )
        )
        
        cut_signal_details = SimpleDetails(
            title="Cut Signal Range",
            content=cut_signal_content,
            expanded=False,
            sizing_mode="stretch_width"
        )
        
        n_neighbors_title = pn.pane.Markdown("### Number of Neighbors", margin=0)
        n_neighbors = pn.widgets.TextInput(
            name="Neighbors",
            value="100, 500, 900",
            placeholder="e.g., 100, 500, 900",
            sizing_mode="stretch_width"
        )
        n_neighbors_tooltip = pn.widgets.TooltipIcon(
            value=Tooltip(
                content="Pattern is integer number and then a comma and go on.", position="left"
            ),
            margin=(16, 0, 0, 0)
        )
        
        n_neighbors_content = pn.Column(
            n_neighbors_title,
            pn.Row(
                n_neighbors,
                n_neighbors_tooltip,
                sizing_mode="stretch_width"
            ),
            sizing_mode="stretch_width",
        )
        
        super().__init__(
            cut_signal_details,
            n_neighbors_content,
            sizing_mode="stretch_width",
            margin=0,
        )
        
    @property
    def min_cut_signal(self) -> pn.widgets.FloatInput:
        return self._min_cut_signal
    @property
    def max_cut_signal(self) -> pn.widgets.FloatInput:
        return self._max_cut_signal