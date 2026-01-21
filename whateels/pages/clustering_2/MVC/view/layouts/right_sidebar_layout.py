import panel as pn, param, numpy as np

from whateels.components import SimpleDetails
from bokeh.models import Tooltip

class _Clustering2RightSidebarParams(param.Parameterized):
    min_eloss = param.Number(
        default=0.1, 
        step=0.1, 
        bounds=(0, 100), 
        label="Min Eloss", 
        doc="Minimum Eloss value for cut signal range."
    )
    max_eloss = param.Number(
        default=100.0, 
        step=0.1, 
        bounds=(0, 100), 
        label="Max Eloss", 
        doc="Maximum Eloss value for cut signal range."
    )
    n_neighbors = param.List(
        default=[100, 500, 900], 
        item_type=int, 
        label="n_neigh",
        doc="List of n_neighbors values for UMAP."
    )
    min_dist = param.List(
        default=[0.1, 0.5, 0.9], 
        item_type=float,
        label="min_dist",
        doc="List of min_dist values for UMAP."
    )

class Clustering2RightSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = "stretch_width"
    
    def __init__(self):
        
        self._params = _Clustering2RightSidebarParams()
                
        self._min_cut_signal = pn.widgets.FloatInput(
            name=type(self._params).param.min_eloss.label,
            value=self._params.min_eloss,
            step=type(self._params).param.min_eloss.step,
            start=type(self._params).param.min_eloss.bounds[0],
            end=type(self._params).param.min_eloss.bounds[1],
            sizing_mode=self._STRETCH_WIDTH
        )
        self._max_cut_signal = pn.widgets.FloatInput(
            name=type(self._params).param.max_eloss.label,
            value=self._params.max_eloss,
            step=type(self._params).param.max_eloss.step,
            start=type(self._params).param.max_eloss.bounds[0],
            end=type(self._params).param.max_eloss.bounds[1],
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
        
        self._n_neighbors = pn.widgets.ArrayInput(
            name=type(self._params).param.n_neighbors.label,
            value=np.array(self._params.n_neighbors, dtype=int),
            placeholder="e.g., 100, 500, 900",
            sizing_mode=self._STRETCH_WIDTH
        )
        
        def _validate_n_neighbors(event):
            arr = event.new
            # Check if all values are integers
            if not np.all(np.equal(np.mod(arr, 1), 0)):
                # Coerce to int if possible
                try:
                    arr_int = arr.astype(int)
                    self._n_neighbors.value = arr_int
                except Exception:
                    self._n_neighbors.value = event.old
        
        self._n_neighbors.param.watch(_validate_n_neighbors, 'value')
        
        # self._n_neighbors.param.watch(self._on_n_neighbors_change, 'value')
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
        
        self._min_dist = pn.widgets.ArrayInput(
            name=type(self._params).param.min_dist.label,
            value=np.array(self._params.min_dist, dtype=float),
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
            title="UMAP",
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
    def n_neighbors(self) -> pn.widgets.ArrayInput:
        return self._n_neighbors
    @property
    def min_dist(self) -> pn.widgets.ArrayInput:
        return self._min_dist