from typing import TYPE_CHECKING, Optional
from whateels.helpers import HTML_ROOT, CSS_ROOT
from whateels.components import UploadedFile
from whateels.base.mvc import BaseView

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
        self._agglomerative_input = None # Dictionary to hold Agglomerative input widgets
        self._spectral_input = None # Dictionary to hold Spectral input widgets

        self._kmeans_run_button = None # Button to run K-Means clustering
        self._background_subtraction_switch = None # Switch for background-subtraction option
        self._store_button = None # Button to store clustering results
        
        self._agglomerative_run_button = None # Button to run Agglomerative clustering
        
        self._spectral_run_button = None # Button to run Spectral clustering

        self._init_components()
        
    @property
    def kmeans_input(self):
        """Access the K-Means input widgets."""
        return self._kmeans_input
    @property
    def kmeans_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the K-Means input widgets."""
        return self._kmeans_run_button      
    
    @property
    def agglomerative_input(self):
        """Access the Agglomerative input widgets."""
        return self._agglomerative_input   
    @property
    def agglomerative_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the Agglomerative run button."""
        return self._agglomerative_run_button
    
    @property
    def spectral_input(self):
        """Access the Spectral input widgets."""
        return self._spectral_input
    @property
    def spectral_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the Spectral run button."""
        return self._spectral_run_button

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout
    
    @property
    def background_subtraction_switch(self):
        """Access the background-subtraction switch widget."""
        return self._background_subtraction_switch
    
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
        uploaded_file = UploadedFile(
            filename=str(self._model.get_uplodaded_filename()), 
            sizing_mode=self.STRETCH_WIDTH, 
            margin=(0,0,10,0)
        )
        left_sidebar = pn.Column(
            uploaded_file,
            sizing_mode=self.STRETCH_WIDTH
        )
        
        return left_sidebar

    def _right_sidebar_layout(self):
        background_subtraction_label = pn.pane.Markdown(
            "### Background-subtraction", 
        )
        self._background_subtraction_switch = pn.widgets.Switch(
            name="Background-subtraction", 
            value=self._model.constants.DEFAULT_BACKGROUND_SUBTRACTION, 
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"]
        )
        background_subtraction_container = pn.Row(
            pn.widgets.TooltipIcon(
                value="Must do Multifitting to enable the switch.", 
                css_classes=["tooltip-icon"]
            ),
            background_subtraction_label,
            self._background_subtraction_switch,
            sizing_mode=self.STRETCH_WIDTH,
            css_classes=["background-subtraction-container"]
        )
        
        k_means_tab = self._create_k_means_tab()
        agglomerative_tab = self._create_agglomerative_tab()
        spectral_tab = self._create_spectral_tab()

        clustering_tabs = pn.Tabs(
            ("K-Means", k_means_tab),
            ("Agglomerative", agglomerative_tab),
            ("Spectral", spectral_tab),
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["clustering-tabs"]
        )
        
        self._store_button = pn.widgets.Button(
            name="Store", 
            button_type="primary", 
            height=55, 
            sizing_mode=self.STRETCH_WIDTH,
            margin=0
        )

        right_sidebar = pn.Column(
            background_subtraction_container,
            clustering_tabs,
            self._store_button,
            sizing_mode=self.STRETCH_BOTH
        )
        return right_sidebar
    
    def _create_k_means_tab(self) -> pn.Column:
        self._kmeans_input = {
            "available_norms": pn.widgets.Select(
                name='Available norms', 
                options=self._model.constants.AVAILABLE_NORMS,
                value=self._model.constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS, 
                step=1, 
                end=20, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_init": pn.widgets.IntInput(
                name="Number of Initializations", 
                value=self._model.constants.DEFAULT_NUMBER_OF_INIT, 
                step=1, 
                end=50, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "max_iter": pn.widgets.IntInput(
                name="Max Iterations", 
                value=self._model.constants.DEFAULT_MAX_ITER, 
                step=10, 
                end=500, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "init_method": pn.widgets.Select(
                name='Initialization Method', 
                options=self._model.constants.AVAILABLE_INIT_METHODS,
                value=self._model.constants.DEFAULT_INIT_METHOD,
                sizing_mode=self.STRETCH_WIDTH
            ),
        }
        
        self._kmeans_run_button = pn.widgets.Button(
            name='Run K-Means',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )
        
        k_means_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._kmeans_input.values()],
                sizing_mode=self.STRETCH_BOTH,
                css_classes=["kmeans-input-container"]
            ),
            self._kmeans_run_button,
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["kmeans-tab"]
        )
        
        return k_means_tab
    
    def _create_agglomerative_tab(self) -> pn.Column:
        agglomerative_input = {
            "available_norms": pn.widgets.Select(
                name='Available norms', 
                options=self._model.constants.AVAILABLE_NORMS,
                value=self._model.constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=5, 
                step=1, 
                end=1000, 
                sizing_mode=self.STRETCH_WIDTH
            ),
            "linkage": pn.widgets.Select(
                name='Linkage Method', 
                options=self._model.constants.AVAILABLE_LINKAGE_METHODS, 
                value=self._model.constants.DEFAULT_LINKAGE,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "affinity": pn.widgets.Select(
                name='Affinity', 
                options=self._model.constants.AVAILABLE_AFFINITIES, 
                value=self._model.constants.DEFAULT_AFFINITY,
                sizing_mode=self.STRETCH_WIDTH,
                disabled=self._model.constants.DEFAULT_LINKAGE == 'ward',
            )
        }

        # store local reference and on-instance reference to avoid "None" typing issues
        self._agglomerative_input = agglomerative_input

        # --- Linkage/Affinity interaction: force affinity to 'euclidean' and disable if linkage is 'ward' ---
        def _on_linkage_change(event):
            linkage_value = event.new
            affinity_widget = agglomerative_input["affinity"]
            if linkage_value == 'ward':
                affinity_widget.value = 'euclidean'
                affinity_widget.disabled = True
            else:
                affinity_widget.disabled = False

        agglomerative_input["linkage"].param.watch(_on_linkage_change, 'value')
        
        self._agglomerative_run_button = pn.widgets.Button(
            name='Run Agglomerative',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )
        
        agglomerative_tab = pn.Column(
            pn.Column(
                *[widget for widget in agglomerative_input.values()],
                sizing_mode=self.STRETCH_BOTH,
                css_classes=["agglomerative-input-container"]
            ),
            self._agglomerative_run_button,
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["agglomerative-tab"]
        )
        
        return agglomerative_tab
    
    def _create_spectral_tab(self) -> pn.Column:
        self._spectral_input = {
            "available_norms": pn.widgets.Select(
                name='Available norms', 
                options=self._model.constants.AVAILABLE_NORMS,
                value=self._model.constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS,
                step=1,
                end=100,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_init": pn.widgets.IntInput(
                name="Number of Initializations",
                value=self._model.constants.DEFAULT_NUMBER_OF_INIT,
                step=1,
                end=100,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "labels_assign_method": pn.widgets.Select(
                name='Labels Assignment Method',
                options=self._model.constants.AVAILABLE_SPECTRAL_ASSIGN_LABELS,
                value=self._model.constants.DEFAULT_SPECTRAL_ASSIGN_LABELS,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "spectral_affinity_metrics": pn.widgets.Select(
                name='Spectral Affinity Metrics',
                options=self._model.constants.AVAILABLE_SPECTRAL_AFFINITIES,
                value=self._model.constants.DEFAULT_SPECTRAL_AFFINITY,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "n_neighbors": pn.widgets.IntInput(
                name="Number of Neighbors",
                value=self._model.constants.DEFAULT_SPECTRAL_N_NEIGHBORS,
                step=1,
                end=1000,
                sizing_mode=self.STRETCH_WIDTH
            ),
            "gamma": pn.widgets.EditableFloatSlider(
                name="Gamma",
                value=self._model.constants.DEFAULT_SPECTRAL_GAMMA,
                start=self._model.constants.DEFAULT_SPECTRAL_GAMMA,
                step=0.5,
                end=10.0,
                sizing_mode=self.STRETCH_WIDTH,
                margin=(10,18,0,18)
            ),
        }
        
        self._spectral_run_button = pn.widgets.Button(
            name='Run Spectral',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self.STRETCH_WIDTH
        )

        spectral_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._spectral_input.values()],
                sizing_mode=self.STRETCH_BOTH,
                css_classes=["spectral-input-container"]
            ),
            self._spectral_run_button,
            sizing_mode=self.STRETCH_BOTH,
            css_classes=["spectral-tab"]
        )
        
        return spectral_tab
    
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