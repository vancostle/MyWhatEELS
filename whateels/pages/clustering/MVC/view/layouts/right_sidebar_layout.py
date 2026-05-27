import panel as pn, json, numpy as np

from whateels.helpers.in_memory_file import InMemoryFile
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ....MVC import ClusteringModel

class ClusteringRightSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    
    def __init__(self, model: "ClusteringModel"):
        self._model = model
        
        self._preprocessing_data_switch = pn.widgets.Switch(
            name="Use Preprocessed Data", 
            value=self._model.constants.DEFAULT_BACKGROUND_SUBTRACTION, 
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"]
        )
    
        self._store_button = pn.widgets.FileDownload(
            label="Store Last Clustering Results",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0, 0, 0),
            icon="download",
            icon_size="20px",
        )

        self._kmeans_input = None  # Dictionary to hold K-Means input widgets
        self._kmeans_color_picker = pn.widgets.ColorPicker(
            name='K-Means Color Picker',
            value='#ffffff',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10,0,0,0),
            disabled=True
        )
        self._kmeans_run_button = pn.widgets.Button(
            name='Run K-Means',
            button_type='success',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH
        )

        self._agglomerative_input = None  # Dictionary to hold Agglomerative input widgets
        self._agglomerative_color_picker = pn.widgets.ColorPicker(
            name='Agglomerative Color Picker',
            value='#ffffff',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10,0,0,0),
            disabled=True
        )
        self._agglomerative_run_button = pn.widgets.Button(
            name='Run Agglomerative',
            button_type='success',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH
        )

        self._spectral_input = None  # Dictionary to hold Spectral input widgets
        self._spectral_color_picker = pn.widgets.ColorPicker(
            name='Spectral Color Picker',
            value='#ffffff',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10,0,0,0),
            disabled=True
        )
        self._spectral_run_button = pn.widgets.Button(
            name='Run Spectral',
            button_type='success',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH
        )

        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_WIDTH
        )
        
    @property
    def preprocessed_data_switch(self) -> pn.widgets.Switch:
        """Access the preprocessed data switch widget."""
        return self._preprocessing_data_switch
    @property
    def spectral_run_button(self) -> pn.widgets.Button:
        """Access the Spectral clustering run button."""
        return self._spectral_run_button
    @property
    def agglomerative_run_button(self) -> pn.widgets.Button:
        """Access the Agglomerative clustering run button."""
        return self._agglomerative_run_button
    @property
    def store_button(self) -> pn.widgets.FileDownload:
        """Access the store button."""
        return self._store_button
    @property
    def kmeans_run_button(self) -> pn.widgets.Button:
        """Access the K-Means clustering run button."""
        return self._kmeans_run_button
    @property
    def spectral_input(self):
        """Access the Spectral clustering input widgets."""
        return self._spectral_input
    @property
    def agglomerative_input(self):
        """Access the Agglomerative clustering input widgets."""
        return self._agglomerative_input
    @property
    def kmeans_input(self):
        """Access the K-Means clustering input widgets."""
        return self._kmeans_input
    @property
    def kmeans_color_picker(self):
        """Access the K-Means color picker widget."""
        return self._kmeans_color_picker
    @property
    def agglomerative_color_picker(self):
        """Access the Agglomerative color picker widget."""
        return self._agglomerative_color_picker
    @property
    def spectral_color_picker(self):
        """Access the Spectral color picker widget."""
        return self._spectral_color_picker
        
    def _create_layout(self):
        background_subtraction_label = pn.pane.Markdown(
            "### Use Preprocessed Data", 
        )

        self._preprocessing_data_switch = pn.widgets.Switch(
            name="Use Preprocessed Data", 
            value=self._model.constants.DEFAULT_BACKGROUND_SUBTRACTION, 
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"]
        )
        
        is_multifitting_available = self._model.is_preprocessed_data_available()
        self._preprocessing_data_switch.disabled = not is_multifitting_available

        preprocessing_data_tooltip = (
            "Enable use of preprocessed data from the home page." 
            if is_multifitting_available else "Must do some preprocessing first at home page before using this option."
        )
        background_subtraction_container = pn.Row(
            pn.widgets.TooltipIcon(
                value=preprocessing_data_tooltip, 
                css_classes=["tooltip-icon"]
            ),
            background_subtraction_label,
            self._preprocessing_data_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-subtraction-container"]
        )

        k_means_tab = self._create_k_means_tab()
        agglomerative_tab = self._create_agglomerative_tab()
        spectral_tab = self._create_spectral_tab()
        
        tab_means_title = self._model.constants.TAB_KMEANS
        tab_agglomerative_title = self._model.constants.TAB_AGGLOMERATIVE
        tab_spectral_title = self._model.constants.TAB_SPECTRAL

        clustering_tabs = pn.Tabs(
            (tab_means_title, k_means_tab),
            (tab_agglomerative_title, agglomerative_tab),
            (tab_spectral_title, spectral_tab),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["clustering-tabs"]
        )
        
        def convert_ndarrays(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {k: convert_ndarrays(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_ndarrays(v) for v in obj]
            else:
                return obj

        def create_file():            
            last_clustering = self._model.last_clustering_result
            
            # Update shared state with the last clustering result
            self._model.app_state.last_clustering_result = last_clustering

            if last_clustering is None:
                return b""
            
            data_to_store_clean = convert_ndarrays(last_clustering)
            json_str = json.dumps(data_to_store_clean)
            
            clustering_type = last_clustering['clustering'].get('type', 'unknown')
            clustering_n = last_clustering['clustering']['inputs'].get('n_clusters', 'unknown')
            
            filename = f"Clustering_{clustering_type}_n_{clustering_n}.json"
            
            if (self._store_button is not None):
                self._store_button.filename = filename
                
            pn.state.notifications.success(f"Clustering results saved as {filename}", duration=5000) #type: ignore
            
            return InMemoryFile(
                json_str.encode('utf-8'), 
                name=filename, 
            )
        
        self._store_button.callback = pn.bind(create_file)

        right_sidebar = pn.Column(
            background_subtraction_container,
            pn.Column(
                clustering_tabs,
                sizing_mode=self._STRETCH_BOTH,
                styles={'flex':'1'}
            ),
            self._store_button,
            styles={'display':'flex'},
            sizing_mode=self._STRETCH_WIDTH
        )

        return right_sidebar
    
    def _create_k_means_tab(self) -> pn.Column:
        constants = self._model.constants

        self._kmeans_input = {
            constants.INPUT_AVAILABLE_NORMS: pn.widgets.Select(
                name='Available norms', 
                options=constants.AVAILABLE_NORMS,
                value=constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_N_CLUSTERS: pn.widgets.IntInput(
                name="Number of Clusters", 
                value=constants.DEFAULT_NUMBER_OF_CLUSTERS, 
                step=1, 
                end=20, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_N_INIT: pn.widgets.IntInput(
                name="Number of Initializations", 
                value=constants.DEFAULT_NUMBER_OF_INIT, 
                step=1, 
                end=50, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_MAX_ITER: pn.widgets.IntInput(
                name="Max Iterations", 
                value=constants.DEFAULT_MAX_ITER, 
                step=10, 
                end=500, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_INIT_METHOD: pn.widgets.Select(
                name='Initialization Method', 
                options=constants.AVAILABLE_INIT_METHODS,
                value=constants.DEFAULT_INIT_METHOD,
                sizing_mode=self._STRETCH_WIDTH
            ),
        }
        
        k_means_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._kmeans_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["kmeans-input-container"]
            ),
            self._kmeans_color_picker,
            self._kmeans_run_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["kmeans-tab"]
        )
        
        return k_means_tab
    
    def _create_agglomerative_tab(self) -> pn.Column:
        constants = self._model.constants

        agglomerative_input = {
            constants.INPUT_AVAILABLE_NORMS: pn.widgets.Select(
                name='Available norms', 
                options=constants.AVAILABLE_NORMS,
                value=constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_N_CLUSTERS: pn.widgets.IntInput(
                name="Number of Clusters", 
                value=5, 
                step=1, 
                end=1000, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_LINKAGE: pn.widgets.Select(
                name='Linkage Method', 
                options=constants.AVAILABLE_LINKAGE_METHODS, 
                value=constants.DEFAULT_LINKAGE,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_AFFINITY: pn.widgets.Select(
                name='Affinity', 
                options=constants.AVAILABLE_AFFINITIES, 
                value=constants.DEFAULT_AFFINITY,
                sizing_mode=self._STRETCH_WIDTH,
                disabled=constants.DEFAULT_LINKAGE == 'ward',
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
        
        agglomerative_tab = pn.Column(
            pn.Column(
                *[widget for widget in agglomerative_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["agglomerative-input-container"]
            ),
            self._agglomerative_color_picker,
            self._agglomerative_run_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["agglomerative-tab"]
        )
        
        return agglomerative_tab
    
    def _create_spectral_tab(self) -> pn.Column:
        constants = self._model.constants
        
        self._spectral_input = {
            constants.INPUT_AVAILABLE_NORMS: pn.widgets.Select(
                name='Available norms', 
                options=constants.AVAILABLE_NORMS,
                value=constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_N_CLUSTERS: pn.widgets.IntInput(
                name="Number of Clusters", 
                value=constants.DEFAULT_NUMBER_OF_CLUSTERS,
                step=1,
                end=100,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_N_INIT: pn.widgets.IntInput(
                name="Number of Initializations",
                value=constants.DEFAULT_NUMBER_OF_INIT,
                step=1,
                end=100,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_LABELS_ASSIGN_METHOD: pn.widgets.Select(
                name='Labels Assignment Method',
                options=constants.AVAILABLE_SPECTRAL_ASSIGN_LABELS,
                value=constants.DEFAULT_SPECTRAL_ASSIGN_LABELS,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_SPECTRAL_AFFINITY: pn.widgets.Select(
                name='Spectral Affinity Metrics',
                options=constants.AVAILABLE_SPECTRAL_AFFINITIES,
                value=constants.DEFAULT_SPECTRAL_AFFINITY,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_SPECTRAL_N_NEIGHBORS: pn.widgets.IntInput(
                name="Number of Neighbors",
                value=constants.DEFAULT_SPECTRAL_N_NEIGHBORS,
                step=1,
                end=1000,
                sizing_mode=self._STRETCH_WIDTH
            ),
            constants.INPUT_SPECTRAL_GAMMA: pn.widgets.EditableFloatSlider(
                name="Gamma",
                value=constants.DEFAULT_SPECTRAL_GAMMA,
                start=constants.DEFAULT_SPECTRAL_GAMMA,
                step=0.5,
                end=10.0,
                sizing_mode=self._STRETCH_WIDTH,
                margin=(10,18,0,18)
            ),
        }

        spectral_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._spectral_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["spectral-input-container"]
            ),
            self._spectral_color_picker,
            self._spectral_run_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["spectral-tab"]
        )
        
        return spectral_tab