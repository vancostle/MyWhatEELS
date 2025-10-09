from typing import TYPE_CHECKING, Optional
from whateels.helpers import HTML_ROOT, CSS_ROOT
from whateels.components import UploadedFile, ErrorPanel
from whateels.base.mvc import BaseView
from whateels.shared_state import AppState

import panel as pn

if TYPE_CHECKING:
    from ..model import ClusteringModel

class ClusteringView(BaseView):
    
    def __init__(self, model: "ClusteringModel"):
        super().__init__(
            model, 
            css_files=[
                str(CSS_ROOT / "clustering.css"),
                str(CSS_ROOT / "dataset_info.css")
            ]
        )
        
        self._model = model
        
        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None
        
        self._kmeans_input = None # Dictionary to hold K-Means input widgets
        self._run_button = None # Button to run K-Means clustering
        self._pre_normalization_switch = None # Switch for pre-normalization option
        self._store_button = None # Button to store clustering results
        
        self._init_components()
        
    @property
    def kmeans_input(self):
        """Access the K-Means input widgets."""
        return self._kmeans_input  
    
    @property
    def run_button(self):
        """Access the K-Means input widgets."""
        return self._run_button         

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    
    @property
    def pre_normalization_switch(self):
        """Access the pre-normalization switch widget."""
        return self._pre_normalization_switch
    
    @property
    def store_button(self):
        """Access the store button widget."""
        return self._store_button
    
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component

    def _init_components(self):
        self.sidebar = self._left_sidebar_layout()
        self.main = self._main_layout()
        self.right_sidebar = self._right_sidebar_layout()

    def _left_sidebar_layout(self):
        app_state = AppState()
        uploaded_file = UploadedFile(filename=str(app_state.filename), sizing_mode=self.STRETCH_WIDTH, margin=(0,0,10,0))
        left_sidebar = pn.Column(
            uploaded_file,
            sizing_mode=self.STRETCH_WIDTH
        )
        
        return left_sidebar

    def _right_sidebar_layout(self):
        pre_normalization_label = pn.pane.Markdown(
            "### Pre-normalization", 
        )
        
        self._pre_normalization_switch = pn.widgets.Switch(
            name="Pre-normalization", 
            value=self._model.constants.DEFAULT_PRE_NORMALIZATION, 
            sizing_mode='stretch_both',
            css_classes=["pre-normalization-switch"]
        )
        pre_normalization_container = pn.Row(
            pre_normalization_label,
            self._pre_normalization_switch,
            sizing_mode=self.STRETCH_WIDTH,
            css_classes=["pre-normalization-container"]
        )
        
        available_norms_select = pn.widgets.Select(
            name='Available norms', 
            options=self._model.constants.AVAILABLE_NORMS,
            value=self._model.constants.DEFAULT_SELECTED_NORM,
        )
        
        available_norms_container = pn.Row(
            available_norms_select,
            sizing_mode=self.STRETCH_WIDTH
        )
        
        k_means_tab = pn.pane.Markdown("Clustering controls go here.", sizing_mode=self.STRETCH_WIDTH)
        agglomerative_tab = pn.pane.Markdown("Dimensionality reduction controls go here.", sizing_mode=self.STRETCH_WIDTH)
        spectral_tab = pn.pane.Markdown("Density-based clustering controls go here.", sizing_mode=self.STRETCH_WIDTH)

        self._kmeans_input = {
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS, 
                step=1, 
                end=1000, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_init": pn.widgets.IntInput(
                name="Number of Initializations", 
                value=self._model.constants.DEFAULT_NUMBER_OF_INIT, 
                step=1, 
                end=1000, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "max_iter": pn.widgets.IntInput(
                name="Max Iterations", 
                value=self._model.constants.DEFAULT_MAX_ITER, 
                step=1, 
                end=10000, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "init_method": pn.widgets.Select(
                name='Initialization Method', 
                options=self._model.constants.INITIALIZATION_METHODS, 
                value=self._model.constants.DEFAULT_INIT_METHOD, 
                sizing_mode=self.STRETCH_WIDTH
            ),
        }

        k_means_tab = pn.Column(
            *[widget for widget in self._kmeans_input.values()],
            sizing_mode=self.STRETCH_BOTH
        )
        
        clustering_hub = pn.Tabs(
            ("K-Means", k_means_tab),
            ("Agglomerative", agglomerative_tab),
            ("Spectral", spectral_tab),
            sizing_mode=self.STRETCH_BOTH
        )
        
        self._run_button = pn.widgets.Button(name="RUN", button_type="success", height=130, sizing_mode=self.STRETCH_WIDTH)
        self._store_button = pn.widgets.Button(name="STORE", button_type="primary", height=130, sizing_mode=self.STRETCH_WIDTH)
        
        buttons_container = pn.Column(
            pn.Row(
                self._run_button,
                self._store_button,
                sizing_mode=self.STRETCH_BOTH,
                css_classes=["clustering-buttons-container"]
            ),
        )

        right_sidebar = pn.Column(
            pre_normalization_container,
            available_norms_container,
            clustering_hub,
            buttons_container,
            sizing_mode=self.STRETCH_BOTH
        )
        return right_sidebar
    
    def create_tab_and_dataset_info(self):
        # File and encoding constants
        HTML_FILE = 'metadata_info.html'
        READ_MODE = 'r'
        UTF_8 = 'utf-8'

        # Panel sizing modes
        STRETCH_WIDTH = "stretch_width"
        
        # CSS classes
        DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
        DATASET_INFO_CLASS = ["dataset-info", "animated"]
        
        # HTML content
        DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
        LABEL_SHAPE = "<strong>Shape:</strong>"
        LABEL_BEAM_ENERGY = "<strong>Beam Energy:</strong>"
        LABEL_CONVERGENCE_ANGLE = "<strong>Convergence Angle:</strong>"
        LABEL_COLLECTION_ANGLE = "<strong>Collection Angle:</strong>"
        
        # Units
        ENERGY_UNIT = " keV"
        ANGLE_UNIT = " mrad"
        
        # Spacing
        SPACER_HEIGHT_SMALL = 5
        SPACER_HEIGHT_MEDIUM = 10
        MARGIN_ZERO = 0
        
        # Fake dataset attributes
        fake_shape = [1024, 1024, 2048]
        fake_beam_energy = 200
        fake_convergence_angle = 5
        fake_collection_angle = 20

        # Load metadata button HTML
        metadata_html_path = HTML_ROOT / HTML_FILE
        with open(metadata_html_path, READ_MODE, encoding=UTF_8) as f:
            metadata_button_html = f.read()

        metadata_button = pn.pane.HTML(metadata_button_html, margin=MARGIN_ZERO)

        # Main info panel
        header = pn.Row(
            pn.pane.HTML(DATASET_INFO_TITLE, sizing_mode=STRETCH_WIDTH, margin=MARGIN_ZERO),
            metadata_button,
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_HEADER_CLASS,
            margin=MARGIN_ZERO
        )

        dataset_info = pn.Column(
            header,
            pn.Spacer(height=SPACER_HEIGHT_SMALL),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_SHAPE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(fake_shape),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_BEAM_ENERGY),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{fake_beam_energy}{ENERGY_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_CONVERGENCE_ANGLE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{fake_convergence_angle}{ANGLE_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_COLLECTION_ANGLE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{fake_collection_angle}{ANGLE_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Spacer(height=SPACER_HEIGHT_MEDIUM),
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_CLASS
        )
        return dataset_info
    
    def _main_layout(self):
        main = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self.STRETCH_BOTH
        )
        return main