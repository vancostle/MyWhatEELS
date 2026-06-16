import panel as pn, param, pickle, io, zipfile, json

from whateels.components import SimpleDetails, ToggleButton
from whateels.helpers import InMemoryFile, SafeConverter
from ..layouts.modals import ExtraUmapParamsModal, HDBSCANGridParamsModal, SVMSettingsModal, SVMTrainSettingsModal

from bokeh.models import Tooltip

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import Clustering2PageModel
    from whateels.components import ModalManager
    from whateels.templates import GeneralPageTemplate

class _Clustering2RightSidebarParams(param.Parameterized):
    available_norms = param.ObjectSelector(
        default='none',
        objects=('none', 'l1', 'l2', 'max'),
        label="Available norms",
        doc="Normalization method applied before UMAP."
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
    hdbscan_min_samples = param.Integer(
        default=4,
        label="min_samples",
        doc="Minimum number of samples for HDBSCAN."
    )
    hdbscan_min_cluster_size = param.Integer(
        default=100,
        label="min_cluster_size",
        doc="Minimum cluster size for HDBSCAN."
    )
    hdbscan_grid_min_cluster_size = param.Integer(
        default=100,
        label="min min_cluster_size",
        doc="Minimum min_cluster_size for HDBSCAN grid evaluation."
    )
    hdbscan_grid_max_cluster_size = param.Integer(
        default=900,
        label="max min_cluster_size",
        doc="Maximum min_cluster_size for HDBSCAN grid evaluation."
    )
    hdbscan_grid_min_samples = param.Integer(
        default=1,
        label="min min_samples",
        doc="Minimum min_samples for HDBSCAN grid evaluation."
    )
    hdbscan_grid_max_samples = param.Integer(
        default=8,
        label="max min_samples",
        doc="Maximum min_samples for HDBSCAN grid evaluation."
    )
    hdbscan_grid_step = param.Integer(
        default=100,
        label="step",
        doc="Step used to sweep min_cluster_size in HDBSCAN grid evaluation."
    )
    svm_min_c = param.Number(
        default=0.1,
        label="min C",
        doc="Minimum C used for SVM evaluation grid.",
    )
    svm_max_c = param.Number(
        default=10.0,
        label="max C",
        doc="Maximum C used for SVM evaluation grid.",
    )
    svm_test_size = param.Number(
        default=0.25,
        label="test_size",
        step=0.01,
        doc="Fraction of dataset reserved for test split.",
    )
    svm_probability = param.Boolean(
        default=False,
        label="Probability",
        doc="Whether to enable probability estimates in SVM.",
    )
    svm_kernel = param.ObjectSelector(
        default="rbf",
        objects=("linear", "rbf", "poly", "sigmoid", "cosine", "sgd"),
        label="kernel",
        doc="Kernel used for SVM/SGD training.",
    )
    svm_gamma = param.String(
        default="scale",
        label="gamma",
        doc="Kernel coefficient for rbf/poly/sigmoid kernels.",
    )
    svm_coef0 = param.Number(
        default=0.0,
        label="coef0",
        doc="Independent term for poly/sigmoid kernels.",
    )
    svm_degree = param.Integer(
        default=3,
        label="degree",
        doc="Degree for poly kernel.",
    )

class Clustering2RightSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = "stretch_width"
    
    _SVG = """
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
    _ACTIVE_SVG = """
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
    
    def __init__(self, model: "Clustering2PageModel", custom_page: "GeneralPageTemplate", modal_manager: "ModalManager"):
        self._model = model
        self._modal_manager = modal_manager
        self._params = _Clustering2RightSidebarParams()
        
        def on_modal_close(params):
            # Update the existing params with values from modal
            self._params.n_components = params.get("n_components", self._params.n_components)
            self._params.metric = params.get("metric", self._params.metric)
            self._params.random_state = params.get("random_state", self._params.random_state)

        def on_hdbscan_grid_modal_close(params):
            self._params.hdbscan_grid_min_cluster_size = params.get(
                "min_cluster_size_min",
                self._params.hdbscan_grid_min_cluster_size,
            )
            self._params.hdbscan_grid_max_cluster_size = params.get(
                "min_cluster_size_max",
                self._params.hdbscan_grid_max_cluster_size,
            )
            self._params.hdbscan_grid_min_samples = params.get(
                "min_samples_min",
                self._params.hdbscan_grid_min_samples,
            )
            self._params.hdbscan_grid_max_samples = params.get(
                "min_samples_max",
                self._params.hdbscan_grid_max_samples,
            )
            self._params.hdbscan_grid_step = params.get(
                "step",
                self._params.hdbscan_grid_step,
            )

        def on_svm_settings_modal_close(params):
            self._params.svm_min_c = params.get("min_c", self._params.svm_min_c)
            self._params.svm_max_c = params.get("max_c", self._params.svm_max_c)

        def on_svm_train_settings_modal_close(params):
            self._params.svm_test_size = params.get("test_size", self._params.svm_test_size)
            self._params.svm_probability = params.get("probability", self._params.svm_probability)
            self._params.svm_gamma = params.get("gamma", self._params.svm_gamma)
            self._params.svm_coef0 = params.get("coef0", self._params.svm_coef0)
            self._params.svm_degree = params.get("degree", self._params.svm_degree)

        self._svm_train_settings_modal = SVMTrainSettingsModal(
            custom_page=custom_page,
            title=model.svm_train_settings_key,
            on_close=on_svm_train_settings_modal_close,
            initial_values={
                "kernel": self._params.svm_kernel,
                "test_size": self._params.svm_test_size,
                "probability": self._params.svm_probability,
                "gamma": self._params.svm_gamma,
                "coef0": self._params.svm_coef0,
                "degree": self._params.svm_degree,
            },
            width=400,
            styles={"padding": "16px"},
        )
        
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
        self._modal_manager.register_modal(
            model.hdbscan_grid_params_key,
            HDBSCANGridParamsModal(
                custom_page=custom_page,
                title=model.hdbscan_grid_params_key,
                on_close=on_hdbscan_grid_modal_close,
                initial_values={
                    "min_cluster_size_min": self._params.hdbscan_grid_min_cluster_size,
                    "min_cluster_size_max": self._params.hdbscan_grid_max_cluster_size,
                    "min_samples_min": self._params.hdbscan_grid_min_samples,
                    "min_samples_max": self._params.hdbscan_grid_max_samples,
                    "step": self._params.hdbscan_grid_step,
                },
                width=400,
                styles={"padding": "16px"},
            )
        )
        self._modal_manager.register_modal(
            model.svm_settings_key,
            SVMSettingsModal(
                custom_page=custom_page,
                title=model.svm_settings_key,
                on_close=on_svm_settings_modal_close,
                initial_values={
                    "min_c": self._params.svm_min_c,
                    "max_c": self._params.svm_max_c,
                },
                width=400,
                styles={"padding": "16px"},
            )
        )
        self._modal_manager.register_modal(
            model.svm_train_settings_key,
            self._svm_train_settings_modal,
        )
        
        # Data source controls
        self._use_preprocessed_data_switch = pn.widgets.Switch()
        
        # UMAP parameters
        self._available_norms = pn.widgets.Select()
        self._n_neighbors = pn.widgets.TextInput()
        self._min_dist = pn.widgets.TextInput()
        self._extra_umap_inputs_button = pn.widgets.ButtonIcon()
        self._compute_umap_embedding_run_button = ToggleButton()
        self._download_results_button = pn.widgets.FileDownload()
        
        # HDBSCAN parameters
        self._hdbscan_selected_umap = pn.widgets.Select()
        self._hdbscan_active_button_icon = pn.widgets.ButtonIcon()
        self._hdbscan_active_button = pn.widgets.Button()
        self._hdbscan_min_samples = pn.widgets.IntInput()
        self._hdbscan_min_cluster_size = pn.widgets.IntInput()
        self._hdbscan_color_picker = pn.widgets.ColorPicker()
        self._compute_hdbscan_on_umap_button = pn.widgets.Button()
        self._download_hdbscan_results_button = pn.widgets.FileDownload()

        # SVM parameters
        self._svm_selected_umap = pn.widgets.Select()
        self._svm_active_button_icon = pn.widgets.ButtonIcon()
        self._svm_active_button = pn.widgets.Button()
        self._svm_kernel = pn.widgets.Select()
        self._svm_C = pn.widgets.FloatInput()
        self._svm_cv = pn.widgets.IntInput()
        self._svm_settings_button = pn.widgets.ButtonIcon()
        self._svm_train_button = pn.widgets.Button()
        self._download_svm_model_button = pn.widgets.FileDownload()
        self._download_svm_results_button = pn.widgets.FileDownload()
        
        # Initialize the layout with the created controls and details
        input_data_controls = self._create_data_source_controls()
        compute_umap_embedding_details = self._create_umap_simple_details(modal_manager, model)
        compute_hdbscan_embedding_details = self._create_hdbscan_simple_details()
        compute_svm_details = self._create_svm_simple_details()
        
        self.disable_hdbscan_controls() # HDBSCAN controls are disabled by default, as they depend on UMAP results, but UMAP results are not available at the beginning.

        super().__init__(
            input_data_controls,
            compute_umap_embedding_details,
            compute_hdbscan_embedding_details,
            compute_svm_details,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
        )

    @property
    def params(self) -> _Clustering2RightSidebarParams:
        return self._params
    @property
    def use_preprocessed_data_switch(self) -> pn.widgets.Switch:
        return self._use_preprocessed_data_switch
    @property
    def available_norms(self) -> pn.widgets.Select:
        return self._available_norms
    @property
    def compute_umap_embedding_run_button(self) -> ToggleButton:
        return self._compute_umap_embedding_run_button
    @property
    def download_results_button(self) -> pn.widgets.FileDownload:
        return self._download_results_button
    @property
    def hdbscan_color_picker(self) -> pn.widgets.ColorPicker:
        return self._hdbscan_color_picker
    @property
    def compute_hdbscan_embedding_run_button(self) -> pn.widgets.Button:
        return self._compute_hdbscan_on_umap_button
    @property
    def download_hdbscan_results_button(self) -> pn.widgets.FileDownload:
        return self._download_hdbscan_results_button
    @property
    def hdbscan_selected_umap(self) -> pn.widgets.Select:
        return self._hdbscan_selected_umap
    @property
    def hdbscan_activate_button(self) -> pn.widgets.Button:
        return self._hdbscan_active_button
    @property
    def svm_selected_umap(self) -> pn.widgets.Select:
        return self._svm_selected_umap
    @property
    def svm_activate_button(self) -> pn.widgets.Button:
        return self._svm_active_button
    @property
    def svm_train_button(self) -> pn.widgets.Button:
        return self._svm_train_button
    @property
    def svm_kernel(self) -> pn.widgets.Select:
        return self._svm_kernel
    @property
    def svm_C(self) -> pn.widgets.FloatInput:
        return self._svm_C
    @property
    def svm_cv(self) -> pn.widgets.IntInput:
        return self._svm_cv
    @property
    def download_svm_model_button(self) -> pn.widgets.FileDownload:
        return self._download_svm_model_button
    @property
    def download_svm_results_button(self) -> pn.widgets.FileDownload:
        return self._download_svm_results_button
    
    def disable_controls(self):
        """ Disable controls in the right sidebar, typically called when UMAP computation is in progress or when UMAP data is loaded from file. Download button is not disabled here, as we want users to be able to download results even when UMAP is computed or loaded. """
        self._use_preprocessed_data_switch.disabled = True
        
        self._available_norms.disabled = True
        self._n_neighbors.disabled = True
        self._min_dist.disabled = True
        
        self._extra_umap_inputs_button.disabled = True
        
        self._compute_umap_embedding_run_button.disabled = True

        self.disable_hdbscan_controls()
        
    def enable_controls(self):
        """ Enable controls in the right sidebar, typically called when UMAP computation is finished or when UMAP data is removed. Download button is not enabled here, as we want users to be able to download results even when UMAP is computed or loaded. """
        self._use_preprocessed_data_switch.disabled = not self._model.is_preprocessed_data_available()
        if self._use_preprocessed_data_switch.disabled:
            self._use_preprocessed_data_switch.value = False
        
        self._available_norms.disabled = False
        self._n_neighbors.disabled = False
        self._min_dist.disabled = False
        
        self._extra_umap_inputs_button.disabled = False
        
        self._compute_umap_embedding_run_button.disabled = False
        
        self.enable_hdbscan_controls() # HDBSCAN controls are enabled separately, as they can be enabled even when UMAP data is loaded or being computed, since they are independent of UMAP results.
        
    def enable_hdbscan_controls(self):
        """ Enable only HDBSCAN controls, typically called when HDBSCAN computation is finished or when HDBSCAN data is removed. """
        self._hdbscan_selected_umap.disabled = False
        self._hdbscan_min_samples.disabled = False
        self._hdbscan_min_cluster_size.disabled = False
        self._hdbscan_active_button.disabled = False
        self._hdbscan_active_button_icon.disabled = False
        
        self._compute_hdbscan_on_umap_button.disabled = False
        self.refresh_hdbscan_download_button()

        self._svm_selected_umap.disabled = False
        self._svm_active_button_icon.disabled = False
        self._svm_active_button.disabled = False
        self._svm_kernel.disabled = False
        self._svm_C.disabled = False
        self._svm_cv.disabled = False
        self._svm_settings_button.disabled = False
        self._svm_train_button.disabled = False
        self.refresh_svm_download_buttons()
        
    def disable_hdbscan_controls(self):
        """ Disable only HDBSCAN controls, typically called when HDBSCAN computation is in progress or when HDBSCAN data is loaded from file. """
        self._hdbscan_selected_umap.disabled = True
        self._hdbscan_min_samples.disabled = True
        self._hdbscan_min_cluster_size.disabled = True
        self._hdbscan_active_button.disabled = True
        self._hdbscan_active_button_icon.disabled = True
        
        self._compute_hdbscan_on_umap_button.disabled = True
        self._download_hdbscan_results_button.disabled = True

        self._svm_selected_umap.disabled = True
        self._svm_active_button_icon.disabled = True
        self._svm_active_button.disabled = True
        self._svm_kernel.disabled = True
        self._svm_C.disabled = True
        self._svm_cv.disabled = True
        self._svm_settings_button.disabled = True
        self._svm_train_button.disabled = True
        self._download_svm_model_button.disabled = True
        self._download_svm_results_button.disabled = True

    def refresh_svm_download_buttons(self) -> None:
        """Enable SVM downloads only after an SVM model/result exists."""
        self._download_svm_model_button.disabled = self._model.svm_model is None
        self._download_svm_results_button.disabled = not bool(self._model.svm_last_result)

    def refresh_hdbscan_download_button(self) -> None:
        """Enable HDBSCAN download only after HDBSCAN results exist."""
        self._download_hdbscan_results_button.disabled = not bool(self._model.hdbscan_last_result)
        
    def _create_data_source_controls(self) -> pn.Row:
        is_preprocessed_available = self._model.is_preprocessed_data_available()

        self._use_preprocessed_data_switch = pn.widgets.Switch(
            name="Use Preprocessed Data",
            value=False,
            disabled=not is_preprocessed_available,
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"],
        )

        availability_message = (
            "Use data preprocessed in Home (Cut Range or other applied preprocessors)."
            if is_preprocessed_available
            else "No preprocessed data available. Apply preprocessing in Home first."
        )

        input_data_label = pn.pane.Markdown("### Use Preprocessed Data")

        input_data_controls = pn.Row(
            pn.widgets.TooltipIcon(
                value=availability_message,
                css_classes=["tooltip-icon"],
            ),
            input_data_label,
            self._use_preprocessed_data_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-subtraction-container"],
        )

        return input_data_controls
        
    def _create_umap_simple_details(self, modal_manager, model) -> SimpleDetails:
        def update_available_norms(event):
            new_value = event.new
            if new_value in type(self._params).param.available_norms.objects:
                self._params.available_norms = new_value
            else:
                self._available_norms.value = event.old

        self._available_norms = pn.widgets.Select(
            name=type(self._params).param.available_norms.label,
            options=list(type(self._params).param.available_norms.objects),
            value=type(self._params).param.available_norms.default,
            sizing_mode=self._STRETCH_WIDTH
        )
        self._available_norms.param.watch(update_available_norms, 'value')

        n_neighbors_str = ', '.join(str(n) for n in type(self._params).param.n_neighbors.default)
        
        self._n_neighbors = pn.widgets.TextInput(
            name=type(self._params).param.n_neighbors.label,
            value=n_neighbors_str,
            placeholder="e.g., 100, 500, 900",
            sizing_mode=self._STRETCH_WIDTH
        )
        
        self._n_neighbors.param.watch(self._validate_n_neighbors, 'value')

        min_dist_str = ', '.join(str(d) for d in type(self._params).param.min_dist.default)
        
        self._min_dist = pn.widgets.TextInput(
            name=type(self._params).param.min_dist.label,
            value=min_dist_str,
            placeholder="e.g., 0.1, 0.5, 0.9",
            sizing_mode=self._STRETCH_WIDTH
        )

        self._min_dist.param.watch(self._validate_min_dist, 'value')

        self._extra_umap_inputs_button = pn.widgets.ButtonIcon(
            icon=self._SVG, 
            active_icon=self._ACTIVE_SVG, 
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
                    "label": "Compute UMAP Embedding(s)",
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
        self._download_results_button.callback = pn.bind(self._create_file)
        
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
            self._available_norms,
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
        
        return SimpleDetails(
            title="UMAP",
            content=compute_umap_embedding_content,
            expanded=True,
            margin=(0, 0, 10, 0),
            sizing_mode=self._STRETCH_WIDTH
        )

    def _create_hdbscan_simple_details(self) -> SimpleDetails:
        """Create the HDBSCAN simple details section. This includes the dropdown to select UMAP embedding, inputs for HDBSCAN parameters, and buttons to activate HDBSCAN controls and compute HDBSCAN on the selected UMAP embedding."""
        
        umap_data_dict_keys = list(self._model.umap_data_dict.keys()) if self._model.umap_data_dict is not None else []
        
        self._hdbscan_selected_umap = pn.widgets.Select(
            name="Select UMAP embedding",
            options=umap_data_dict_keys,
            sizing_mode=self._STRETCH_WIDTH
        )
        
        self._hdbscan_active_button = pn.widgets.Button(
            name="Evaluate",
            button_type="warning",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(6, 0, 10, 10)
        )

        self._hdbscan_active_button_icon = pn.widgets.ButtonIcon(
            icon=self._SVG,
            active_icon=self._ACTIVE_SVG,
            size='2em',
            margin=(0, 0, 0, 10),
            styles={
                "cursor": "pointer",
                "display": "grid",
                "place-items": "center",
                "border-radius": "6px"
            },
        )
        self._hdbscan_active_button_icon.on_click(
            lambda _: self._modal_manager.open_modal(self._model.hdbscan_grid_params_key)
        )
        
        def update_hdbscan_min_samples(event):
            new_value = event.new
            if new_value is not None and new_value > 0:
                self._params.hdbscan_min_samples = new_value
            else:
                self._hdbscan_min_samples.value = event.old  # Revert to old value if new value is invalid
          
        self._hdbscan_min_samples = pn.widgets.IntInput(
            name=type(self._params).param.hdbscan_min_samples.label,
            value=type(self._params).param.hdbscan_min_samples.default,
            placeholder="e.g., 1",
            sizing_mode=self._STRETCH_WIDTH
        )
        
        self._hdbscan_min_samples.param.watch(update_hdbscan_min_samples, 'value')
        
        self._hdbscan_min_cluster_size = pn.widgets.IntInput(
            name=type(self._params).param.hdbscan_min_cluster_size.label,
            value=type(self._params).param.hdbscan_min_cluster_size.default,
            placeholder="e.g., 400",
            sizing_mode=self._STRETCH_WIDTH
        )

        def update_hdbscan_min_cluster_size(event):
            new_value = event.new
            if new_value is not None and new_value > 0:
                self._params.hdbscan_min_cluster_size = new_value
            else:
                self._hdbscan_min_cluster_size.value = event.old  # Revert to old value if new value is invalid

        self._hdbscan_min_cluster_size.param.watch(update_hdbscan_min_cluster_size, 'value')

        self._hdbscan_color_picker = pn.widgets.ColorPicker(
            name="HDBSCAN Cluster Color",
            value="#ffffff",
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True, # Color picker is disabled by default, as it depends on HDBSCAN results, but HDBSCAN results are not available at the beginning.
            styles={"padding" : "0"}
        )

        self._compute_hdbscan_on_umap_button = pn.widgets.Button(
            name="Compute HDBSCAN on UMAP",
            button_type="success",
            height=55,
            margin=(10, 0, 0, 0),
            sizing_mode=self._STRETCH_WIDTH
        )

        self._download_hdbscan_results_button = pn.widgets.FileDownload(
            label="Download Results",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0, 0, 0),
            icon="download",
            icon_size="20px",
        )
        self._download_hdbscan_results_button.disabled = True
        self._download_hdbscan_results_button.callback = pn.bind(self._create_hdbscan_results_file)
            
        compute_hdbscan_embedding_content = pn.Column(
            self._hdbscan_selected_umap,
            pn.Row(
                pn.Column(
                    self._hdbscan_active_button_icon,
                    margin=(11, 0, 0, 0),
                    height=55,
                ),
                self._hdbscan_active_button,
                sizing_mode=self._STRETCH_WIDTH,
                height=55,
                margin=(10, 0, 0, 0),
                styles={"display": "flex"}
            ),
            self._hdbscan_min_samples,
            self._hdbscan_min_cluster_size,
            pn.Column(
                self._hdbscan_color_picker,
                self._compute_hdbscan_on_umap_button,
                sizing_mode=self._STRETCH_WIDTH,
            ),
            self._download_hdbscan_results_button,
        )
        
        return SimpleDetails(
            title="HDBSCAN",
            content=compute_hdbscan_embedding_content,
            expanded=False,
            margin=(0, 0, 10, 0),
            sizing_mode=self._STRETCH_WIDTH
        )

    def _create_svm_simple_details(self) -> SimpleDetails:
        """Create the SVM simple details section with controls for training and exports."""
        umap_data_dict_keys = list(self._model.umap_data_dict.keys()) if self._model.umap_data_dict is not None else []

        self._svm_selected_umap = pn.widgets.Select(
            name="Select UMAP embedding",
            options=umap_data_dict_keys,
            sizing_mode=self._STRETCH_WIDTH
        )

        self._svm_active_button = pn.widgets.Button(
            name="Evaluate",
            button_type="warning",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(6, 0, 10, 10)
        )

        self._svm_active_button_icon = pn.widgets.ButtonIcon(
            icon=self._SVG,
            active_icon=self._ACTIVE_SVG,
            size='2em',
            margin=(0, 0, 0, 10),
            styles={
                "cursor": "pointer",
                "display": "grid",
                "place-items": "center",
                "border-radius": "6px"
            },
        )
        self._svm_active_button_icon.on_click(
            lambda _: self._modal_manager.open_modal(self._model.svm_settings_key)
        )

        self._svm_kernel = pn.widgets.Select(
            name="kernel",
            options=list(type(self._params).param.svm_kernel.objects),
            value=str(self._params.svm_kernel),
            sizing_mode=self._STRETCH_WIDTH,
        )

        def on_svm_kernel_change(event):
            kernel = str(event.new).lower().strip()
            if kernel not in type(self._params).param.svm_kernel.objects:
                self._svm_kernel.value = event.old
                return
            self._params.svm_kernel = kernel
            self._svm_train_settings_modal.set_selected_kernel(kernel)

        self._svm_kernel.param.watch(on_svm_kernel_change, "value")

        self._svm_C = pn.widgets.FloatInput(
            name="C",
            value=1.0,
            step=0.1,
            start=0.0001,
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._svm_cv = pn.widgets.IntInput(
            name="cv",
            value=100,
            step=1,
            start=2,
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._svm_settings_button = pn.widgets.ButtonIcon(
            icon=self._SVG,
            active_icon=self._ACTIVE_SVG,
            size='2em',
            margin=(0, 0, 0, 10),
            styles={
                "cursor": "pointer",
                "display": "grid",
                "place-items": "center",
                "border-radius": "6px"
            },
        )
        self._svm_settings_button.on_click(
            lambda _: (
                self._svm_train_settings_modal.set_selected_kernel(self._svm_kernel.value),
                self._modal_manager.open_modal(self._model.svm_train_settings_key),
            )
        )

        self._svm_train_button = pn.widgets.Button(
            name="Train SVM",
            button_type="success",
            height=55,
            margin=0, 
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._download_svm_model_button = pn.widgets.FileDownload(
            label="Download SVM model",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0, 0, 0),
            icon="download",
            icon_size="20px",
        )

        self._download_svm_model_button.disabled = True
        self._download_svm_model_button.callback = pn.bind(self._create_svm_model_file)

        self._download_svm_results_button = pn.widgets.FileDownload(
            label="Download Results",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0, 0, 0),
            icon="download",
            icon_size="20px",
        )
        self._download_svm_results_button.disabled = True
        self._download_svm_results_button.callback = pn.bind(self._create_svm_results_file)

        svm_content = pn.Column(
            self._svm_kernel,
            pn.Row(
                pn.Column(
                    self._svm_active_button_icon,
                    margin=(11, 0, 0, 0),
                    height=55,
                ),
                self._svm_active_button,
                sizing_mode=self._STRETCH_WIDTH,
                height=55,
                margin=(10, 0, 0, 0),
                styles={"display": "flex"}
            ),
            self._svm_C,
            self._svm_cv,
            pn.Row(
                pn.Column(
                    self._svm_settings_button,
                    margin=0,
                    height=55,
                    styles={
                        "display": "flex",
                        "align-items": "center",
                        "justify-content": "center",
                    }
                ),
                self._svm_train_button,
                sizing_mode=self._STRETCH_WIDTH,
                height=55,
                margin=(10, 0, 0, 0),
                styles={"display": "flex", "justify-content": "center", "align-items": "center", "gap": "10px"}
            ),
            self._download_svm_results_button,
            self._download_svm_model_button,
            sizing_mode=self._STRETCH_WIDTH,
        )

        return SimpleDetails(
            title="SVM",
            content=svm_content,
            expanded=False,
            margin=(0, 0, 10, 0),
            sizing_mode=self._STRETCH_WIDTH,
        )
        
    def _validate_n_neighbors(self, event):
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
            
    def _validate_min_dist(self, event):
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
 
    def _create_file(self):            
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

    @classmethod
    def _to_serializable(cls, obj):
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if isinstance(obj, dict):
            return {str(key): cls._to_serializable(value) for key, value in obj.items()}
        if isinstance(obj, (list, tuple, set)):
            return [cls._to_serializable(value) for value in obj]
        return obj

    @staticmethod
    def _safe_filename_part(value) -> str:
        text = str(value) if value is not None else "unknown"
        for char in ('/', '\\', ':', '*', '?', '"', '<', '>', '|', ' '):
            text = text.replace(char, "_")
        return text

    def _build_svm_download_filename(self, prefix: str, extension: str) -> str:
        result = self._model.svm_last_result or {}
        clustering = result.get("clustering", {})
        inputs = clustering.get("inputs", {})
        kernel = self._safe_filename_part(inputs.get("kernel", "unknown"))
        c_value = self._safe_filename_part(inputs.get("C", "unknown"))
        return f"{prefix}_{kernel}_C_{c_value}.{extension}"

    def _build_hdbscan_download_filename(self) -> str:
        result = self._model.hdbscan_last_result or {}
        clustering = result.get("clustering", {})
        inputs = clustering.get("inputs", {})
        norm = self._safe_filename_part(inputs.get("available_norms", "unknown"))
        min_samples = self._safe_filename_part(inputs.get("min_samples", "unknown"))
        min_cluster_size = self._safe_filename_part(inputs.get("min_cluster_size", "unknown"))
        return f"hdbscan_clustering_results_{norm}_min_samples_{min_samples}_min_cluster_size_{min_cluster_size}.json"

    def _create_hdbscan_results_file(self):
        hdbscan_result = self._model.hdbscan_last_result
        if not hdbscan_result:
            pn.state.notifications.warning("Compute HDBSCAN before downloading the results.", duration=5000) #type: ignore
            return b""

        data_to_store_clean = self._to_serializable(hdbscan_result)
        json_str = json.dumps(data_to_store_clean)
        filename = self._build_hdbscan_download_filename()

        if self._download_hdbscan_results_button is not None:
            self._download_hdbscan_results_button.filename = filename

        pn.state.notifications.success(f"HDBSCAN clustering results saved as {filename}", duration=5000) #type: ignore

        return InMemoryFile(
            json_str.encode("utf-8"),
            name=filename,
        )

    def _create_svm_model_file(self):
        svm_model = self._model.svm_model
        if svm_model is None:
            pn.state.notifications.warning("Train SVM before downloading the model.", duration=5000) #type: ignore
            return b""

        result = self._model.svm_last_result or {}
        clustering = result.get("clustering", {})
        payload = {
            "model": svm_model,
            "metadata": {
                "file": clustering.get("file"),
                "spectrum_image": clustering.get("spectrum_image"),
                "type": clustering.get("type"),
                "inputs": clustering.get("inputs", {}),
                "metrics": clustering.get("metrics", {}),
            },
        }
        filename = self._build_svm_download_filename("svm_model", "pkl")

        if self._download_svm_model_button is not None:
            self._download_svm_model_button.filename = filename

        pn.state.notifications.success(f"SVM model saved as {filename}", duration=5000) #type: ignore

        return InMemoryFile(
            pickle.dumps(payload),
            name=filename,
        )

    def _create_svm_results_file(self):
        svm_result = self._model.svm_last_result
        if not svm_result:
            pn.state.notifications.warning("Train SVM before downloading the results.", duration=5000) #type: ignore
            return b""

        data_to_store_clean = self._to_serializable(svm_result)
        json_str = json.dumps(data_to_store_clean)
        filename = self._build_svm_download_filename("svm_clustering_results", "json")

        if self._download_svm_results_button is not None:
            self._download_svm_results_button.filename = filename

        pn.state.notifications.success(f"SVM clustering results saved as {filename}", duration=5000) #type: ignore

        return InMemoryFile(
            json_str.encode("utf-8"),
            name=filename,
        )
