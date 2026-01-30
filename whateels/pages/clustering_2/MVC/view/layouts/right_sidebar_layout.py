import panel as pn, param

from whateels.components import SimpleDetails, ToggleButton
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
        
        n_neighbors_str = ', '.join(str(n) for n in type(self._params).param.n_neighbors.default)
        
        n_neighbors = pn.widgets.TextInput(
            name=type(self._params).param.n_neighbors.label,
            value=n_neighbors_str,
            placeholder="e.g., 100, 500, 900",
            sizing_mode=self._STRETCH_WIDTH
        )
        
        def validate_n_neighbors(event):
            value = event.new
            try:
                str_values = [v.strip() for v in value.split(',')]
                int_values = [int(v) for v in str_values if v]
                if all(v > 0 for v in int_values):
                    self._params.n_neighbors = int_values
                else:
                    raise ValueError
            except ValueError:
                n_neighbors.value = event.old
        
        n_neighbors.param.watch(validate_n_neighbors, 'value')
        
        # self._n_neighbors.param.watch(self._on_n_neighbors_change, 'value')
        n_neighbors_tooltip = pn.widgets.TooltipIcon(
            value=Tooltip(
                content="Pattern is integer number and then a comma and go on.", position="left"
            ),
            margin=(16, 0, 0, 0)
        )
        n_neighbors_content = pn.Row(
            n_neighbors,
            n_neighbors_tooltip,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        min_dist_str = ', '.join(str(d) for d in type(self._params).param.min_dist.default)
        
        min_dist = pn.widgets.TextInput(
            name=type(self._params).param.min_dist.label,
            value=min_dist_str,
            placeholder="e.g., 0.1, 0.5, 0.9",
            sizing_mode=self._STRETCH_WIDTH
        )
        
        def validate_min_dist(event):
            value = event.new
            try:
                str_values = [v.strip() for v in value.split(',')]
                float_values = []
                for v in str_values:
                    if v:
                        float_values.append(float(v))
                self._params.min_dist = float_values
                # Always reformat the input as floats (e.g., 5 -> 5.0)
                min_dist.value = ', '.join(str(float(v)) for v in float_values)
            except ValueError:
                min_dist.value = event.old

        min_dist.param.watch(validate_min_dist, 'value')
        
        min_dist_tooltip = pn.widgets.TooltipIcon(
            value=Tooltip(
                content="Pattern is float number and then a comma and go on.", position="left"
            ),
            margin=(16, 0, 0, 0)
        )
        min_dist_content = pn.Row(
            min_dist, 
            min_dist_tooltip,
            sizing_mode=self._STRETCH_WIDTH
        )
    
        # self._compute_umap_embedding_run_button = pn.widgets.Button(
        #     name='Compute UMAP embedding',
        #     button_type='success',
        #     height=55,
        #     margin=(20,0,0,0),
        #     sizing_mode=self._STRETCH_WIDTH
        # )

        self._compute_umap_embedding_run_button = ToggleButton(
            height=55,
            initial_state=True,
            states={
                "on": {
                    "label": "Compute UMAP Embedding",
                    "on_click": lambda : print("UMAP computation started"),
                    "button_type": "success",
                },
                "off": {
                    "label": "Cancel Next UMAP Computation",
                    "on_click": lambda : print("UMAP computation cancelled"),
                    "button_type": "danger",
                }
            },
            margin=(20,0,0,0),
            sizing_mode=self._STRETCH_WIDTH
        )
        
        self._download_results_button = pn.widgets.Button(
            name='Download Results',
            button_type='primary',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True
        )
        
        compute_umap_embedding_content = pn.Column(
            n_neighbors_content,
            min_dist_content,
            self._compute_umap_embedding_run_button,
            self._download_results_button,
        )
        compute_umap_embedding_details = SimpleDetails(
            title="UMAP",
            content=compute_umap_embedding_content,
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH
        )

        super().__init__(
            cut_signal_details,
            compute_umap_embedding_details,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
        )

    @property
    def params(self) -> _Clustering2RightSidebarParams:
        return self._params
    @property
    def min_cut_signal(self) -> pn.widgets.FloatInput:
        return self._min_cut_signal
    @property
    def max_cut_signal(self) -> pn.widgets.FloatInput:
        return self._max_cut_signal
    @property
    def compute_umap_embedding_run_button(self) -> ToggleButton:
        return self._compute_umap_embedding_run_button
    @property
    def download_results_button(self) -> pn.widgets.Button:
        return self._download_results_button