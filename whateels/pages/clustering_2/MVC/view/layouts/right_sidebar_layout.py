import panel as pn, param, pickle, io, zipfile

from whateels.components import SimpleDetails, ToggleButton
from whateels.helpers.in_memory_file import InMemoryFile
from ..layouts.modals import ExtraUmapParamsModal

from bokeh.models import Tooltip

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Clustering2PageModel
    from whateels.components import ModalManager
    from whateels.templates import GeneralPageTemplate

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
    n_components = param.Integer(
        default=2,
        label="n_components",
        doc="Number of components for UMAP embedding."
    )
    metric = param.String(
        default="euclidean",
        label="metric",
        doc="Distance metric for UMAP."
    )
    random_state = param.Integer(
        default=2,
        label="random_state",
        doc="Random state for UMAP."
    )

class Clustering2RightSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = "stretch_width"
    
    def __init__(self, model: "Clustering2PageModel", custom_page: "GeneralPageTemplate", modal_manager: "ModalManager"):
        self._model = model
        self._modal_manager = modal_manager
        self._params = _Clustering2RightSidebarParams()
        
        def on_modal_close(params):
            # Update the existing params with values from modal
            self._params.n_components = params.get("n_components", self._params.n_components)
            self._params.metric = params.get("metric", self._params.metric)
            self._params.random_state = params.get("random_state", self._params.random_state)
        
        self._modal_manager.register_modal(
            'Extra UMAP Parameters',
            ExtraUmapParamsModal(
                custom_page=custom_page,
                title=model.extra_umap_params_key,
                on_close=on_modal_close,
                width=400,
                styles={"padding": "16px"}
            )
        )
                
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
        
        self._n_neighbors = pn.widgets.TextInput(
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
                self._n_neighbors.value = event.old
        
        self._n_neighbors.param.watch(validate_n_neighbors, 'value')
        
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
        
        min_dist_str = ', '.join(str(d) for d in type(self._params).param.min_dist.default)
        
        self._min_dist = pn.widgets.TextInput(
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
                self._min_dist.value = ', '.join(str(float(v)) for v in float_values)
            except ValueError:
                self._min_dist.value = event.old

        self._min_dist.param.watch(validate_min_dist, 'value')
        
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
        
        SVG = """
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-adjustments-horizontal" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <circle cx="14" cy="6" r="2" />
            <line x1="4" y1="6" x2="12" y2="6" />
            <line x1="16" y1="6" x2="20" y2="6" />
            <circle cx="8" cy="12" r="2" />
            <line x1="4" y1="12" x2="6" y2="12" />
            <line x1="10" y1="12" x2="20" y2="12" />
            <circle cx="17" cy="18" r="2" />
            <line x1="4" y1="18" x2="15" y2="18" />
            <line x1="19" y1="18" x2="20" y2="18" />
            </svg>
        """
        ACTIVE_SVG = """
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-adjustments-horizontal" width="24" height="24" viewBox="0 0 24 24" stroke-width="2" style="--secondary-whateels-background: #b63fb5;" stroke="var(--secondary-whateels-background)" fill="none" stroke-linecap="round" stroke-linejoin="round">
            <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
            <circle cx="14" cy="6" r="2" fill="var(--secondary-whateels-background)" stroke="var(--secondary-whateels-background)" />
            <line x1="4" y1="6" x2="12" y2="6" />
            <line x1="16" y1="6" x2="20" y2="6" />
            <circle cx="8" cy="12" r="2" fill="var(--secondary-whateels-background)" stroke="var(--secondary-whateels-background)" />
            <line x1="4" y1="12" x2="6" y2="12" />
            <line x1="10" y1="12" x2="20" y2="12" />
            <circle cx="17" cy="18" r="2" fill="var(--secondary-whateels-background)" stroke="var(--secondary-whateels-background)" />
            <line x1="4" y1="18" x2="15" y2="18" />
            <line x1="19" y1="18" x2="20" y2="18" />
            </svg>
        """

        self._extra_umap_inputs_button = pn.widgets.ButtonIcon(
            icon=SVG, 
            active_icon=ACTIVE_SVG, 
            size='2em',
            margin=(0, 0, 0, 10),
            styles={
                "cursor": "pointer",
                "display": "grid",
                "place-items": "center",
                "border-radius": "6px"
            },
        )
        
        self._extra_umap_inputs_button.on_click(lambda _ : modal_manager.open_modal(model.extra_umap_params_key))

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
            margin=0,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        self._download_results_button = pn.widgets.FileDownload(
            label="Download Results",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0, 0, 0),
            icon="download",
            icon_size="20px",
        )
        
        self._download_results_button.disabled = True
        
        def create_file():            
            umap_data_dict = self._model.umap_data_dict
            
            if umap_data_dict is None:
                return b""
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for key, value in umap_data_dict.items():
                    file_data = pickle.dumps(value)
                    safe_key = str(key).replace("/", "_").replace("\\", "_")
                    filename = f"{safe_key}.pkl"
                    zip_file.writestr(filename, file_data)
            zip_buffer.seek(0)        
            filename = "umap_results.zip"

            if (self._download_results_button is not None):
                self._download_results_button.filename = filename

            pn.state.notifications.success(f"Clustering results saved as {filename}", duration=5000) #type: ignore

            return InMemoryFile(
                zip_buffer.read(), 
                name=filename, 
            )
        
        self._download_results_button.callback = pn.bind(create_file)
        
        compute_umap_embedding_content = pn.Column(
            n_neighbors_content,
            min_dist_content,
            pn.Row(
                pn.Column(
                    self._extra_umap_inputs_button,
                    margin=0,
                    height=55,
                    styles={
                        "display": "flex", 
                        "align-items": "center", 
                        "justify-content": "center",
                    }
                ),
                self._compute_umap_embedding_run_button,
                sizing_mode=self._STRETCH_WIDTH,
                height=55,
                margin=(10, 0, 0, 0),
                styles={"display": "flex", "justify-content": "center", "align-items": "center", "gap": "10px"}
            ),
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
    def download_results_button(self) -> pn.widgets.FileDownload:
        return self._download_results_button
    
    def disable_controls(self):
        self._min_cut_signal.disabled = True
        self._max_cut_signal.disabled = True
        
        self._n_neighbors.disabled = True
        self._min_dist.disabled = True
        self._extra_umap_inputs_button.disabled = True
        
        self._compute_umap_embedding_run_button.disabled = True
        self._download_results_button.disabled = True
        
    def enable_controls(self):
        self._min_cut_signal.disabled = False
        self._max_cut_signal.disabled = False
        
        self._n_neighbors.disabled = False
        self._min_dist.disabled = False
        self._extra_umap_inputs_button.disabled = False
        
        self._compute_umap_embedding_run_button.disabled = False
        self._download_results_button.disabled = False