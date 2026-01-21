import panel as pn

from whateels.components import SimpleDetails
from bokeh.models import Tooltip

class Clustering2RightSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = "stretch_width"
    
    def __init__(self):
                
        self._min_cut_signal = pn.widgets.FloatInput(
            name="Min Eloss",
            value=0.1,
            step=0.1,
            start=0.0,
            end=100.0,
            sizing_mode=self._STRETCH_WIDTH
        )
        self._max_cut_signal = pn.widgets.FloatInput(
            name="Max Eloss",
            value=100.0,
            step=0.1,
            start=99.9,
            end=100.0,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        cut_signal_content = pn.Column(
            pn.Row(
                self._min_cut_signal,
                self._max_cut_signal,
                sizing_mode=self._STRETCH_WIDTH,
            )
        )
        
        cut_signal_details = SimpleDetails(
            title="Cut Signal Range",
            content=cut_signal_content,
            expanded=False,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 0, 10, 0)
        )
        
        self._n_neighbors = pn.widgets.TextInput(
            name="n_neigh",
            value="100, 500, 900",
            placeholder="e.g., 100, 500, 900",
            sizing_mode=self._STRETCH_WIDTH
        )
        n_neighbors_tooltip = pn.widgets.TooltipIcon(
            value=Tooltip(
                content="Pattern is integer number and then a comma and go on.", position="left"
            ),
            margin=(16, 0, 0, 0)
        )
        n_neighbors_content = pn.Row(
            self._n_neighbors,
            n_neighbors_tooltip,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        self._min_dist = pn.widgets.TextInput(
            name="min_dist",
            value="0.1, 0.5, 0.9",
            placeholder="e.g., 0.1, 0.5, 0.9",
            sizing_mode=self._STRETCH_WIDTH
        )
        min_dist_tooltip = pn.widgets.TooltipIcon(
            value=Tooltip(
                content="Pattern is float number and then a comma and go on.", position="left"
            ),
            margin=(16, 0, 0, 0)
        )
        min_dist_content = pn.Row(
            self._min_dist, 
            min_dist_tooltip,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        compute_umap_embedding_content = pn.Column(
            n_neighbors_content,
            min_dist_content,
        )
        compute_umap_embedding = SimpleDetails(
            title="Compute UMAP Embedding",
            content=compute_umap_embedding_content,
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        run_button = pn.widgets.Button(
            name='Compute umap embedding',
            button_type='success',
            height=55,
            margin=(20,0,0,0),
            sizing_mode=self._STRETCH_WIDTH
        )
        
        super().__init__(
            cut_signal_details,
            compute_umap_embedding,
            run_button,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
        )
        
    @property
    def min_cut_signal(self) -> pn.widgets.FloatInput:
        return self._min_cut_signal
    @property
    def max_cut_signal(self) -> pn.widgets.FloatInput:
        return self._max_cut_signal
    @property
    def n_neighbors(self) -> pn.widgets.TextInput:
        return self._n_neighbors
    @property
    def min_dist(self) -> pn.widgets.TextInput:
        return self._min_dist