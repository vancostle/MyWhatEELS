import panel as pn

class Clustering2RightSidebarLayout(pn.Column):
    
    def __init__(self):
        
        cut_signal_title = pn.pane.Markdown("### Cut Signal", margin=0)
        
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
        
        cut_signal_container = pn.Column(
            cut_signal_title,
            pn.Row(
                self._min_cut_signal,
                self._max_cut_signal,
                sizing_mode="stretch_width",
            )
        )
        
        super().__init__(
            cut_signal_container,
            sizing_mode="stretch_width",
            margin=0,
        )
        
    @property
    def min_cut_signal(self) -> pn.widgets.FloatInput:
        return self._min_cut_signal
    @property
    def max_cut_signal(self) -> pn.widgets.FloatInput:
        return self._max_cut_signal