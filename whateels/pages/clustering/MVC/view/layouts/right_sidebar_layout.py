import panel as pn

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ....MVC import ClusteringModel

class ClusteringRightSidebarLayout(pn.Column):
    
    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    
    def __init__(self, model: "ClusteringModel"):
        self._model = model
        
        self._background_subtraction_switch = None  # Switch for background-subtraction option
        self._store_button = None  # Button to store clustering results
        self._kmeans_input = None  # Dictionary to hold K-Means input widgets
        self._kmeans_run_button = None  # Button to run K-Means clustering
        self._agglomerative_input = None  # Dictionary to hold Agglomerative input widgets
        self._agglomerative_run_button = None  # Button to run Agglomerative clustering
        self._spectral_input = None  # Dictionary to hold Spectral input widgets
        self._spectral_run_button = None  # Button to run Spectral clustering

        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_WIDTH
        )
        
    @property
    def background_subtraction_switch(self) -> Optional[pn.widgets.Switch]:
        """Access the background-subtraction switch widget."""
        return self._background_subtraction_switch
    @property
    def spectral_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the Spectral clustering run button."""
        return self._spectral_run_button
    @property
    def agglomerative_run_button(self) -> Optional[pn.widgets.Button]:
        """Access the Agglomerative clustering run button."""
        return self._agglomerative_run_button
    @property
    def store_button(self) -> Optional[pn.widgets.Button]:
        """Access the store button."""
        return self._store_button
    @property
    def kmeans_run_button(self) -> Optional[pn.widgets.Button]:
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
        
    def _create_layout(self):
        background_subtraction_label = pn.pane.Markdown(
            "### Background-subtraction", 
        )

        self._background_subtraction_switch = pn.widgets.Switch(
            name="Background-subtraction", 
            value=self._model.constants.DEFAULT_BACKGROUND_SUBTRACTION, 
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"]
        )

        is_multifitting_available = self._model.is_multifit_available()
        self._background_subtraction_switch.disabled = not is_multifitting_available

        subtraction_bg_tooltip = (
            "Enable background-subtraction from multifit results." 
            if is_multifitting_available else "Must do Multifitting to enable the switch."
        )
        background_subtraction_container = pn.Row(
            pn.widgets.TooltipIcon(
                value=subtraction_bg_tooltip, 
                css_classes=["tooltip-icon"]
            ),
            background_subtraction_label,
            self._background_subtraction_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-subtraction-container"]
        )

        k_means_tab = self._create_k_means_tab()
        agglomerative_tab = self._create_agglomerative_tab()
        spectral_tab = self._create_spectral_tab()

        clustering_tabs = pn.Tabs(
            ("K-Means", k_means_tab),
            ("Agglomerative", agglomerative_tab),
            ("Spectral", spectral_tab),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["clustering-tabs"]
        )
        
        self._store_button = pn.widgets.Button(
            name="Store", 
            button_type="primary", 
            height=55, 
            sizing_mode=self._STRETCH_WIDTH,
            margin=0
        )

        right_sidebar = pn.Column(
            background_subtraction_container,
            clustering_tabs,
            self._store_button,
            sizing_mode=self._STRETCH_WIDTH
        )

        return right_sidebar
    
    def _create_k_means_tab(self) -> pn.Column:
        self._kmeans_input = {
            "available_norms": pn.widgets.Select(
                name='Available norms', 
                options=self._model.constants.AVAILABLE_NORMS,
                value=self._model.constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS, 
                step=1, 
                end=20, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            "n_init": pn.widgets.IntInput(
                name="Number of Initializations", 
                value=self._model.constants.DEFAULT_NUMBER_OF_INIT, 
                step=1, 
                end=50, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            "max_iter": pn.widgets.IntInput(
                name="Max Iterations", 
                value=self._model.constants.DEFAULT_MAX_ITER, 
                step=10, 
                end=500, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            "init_method": pn.widgets.Select(
                name='Initialization Method', 
                options=self._model.constants.AVAILABLE_INIT_METHODS,
                value=self._model.constants.DEFAULT_INIT_METHOD,
                sizing_mode=self._STRETCH_WIDTH
            ),
        }
        
        self._kmeans_run_button = pn.widgets.Button(
            name='Run K-Means',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self._STRETCH_WIDTH
        )
        
        k_means_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._kmeans_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["kmeans-input-container"]
            ),
            self._kmeans_run_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["kmeans-tab"]
        )
        
        return k_means_tab
    
    def _create_agglomerative_tab(self) -> pn.Column:
        agglomerative_input = {
            "available_norms": pn.widgets.Select(
                name='Available norms', 
                options=self._model.constants.AVAILABLE_NORMS,
                value=self._model.constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=5, 
                step=1, 
                end=1000, 
                sizing_mode=self._STRETCH_WIDTH
            ),
            "linkage": pn.widgets.Select(
                name='Linkage Method', 
                options=self._model.constants.AVAILABLE_LINKAGE_METHODS, 
                value=self._model.constants.DEFAULT_LINKAGE,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "affinity": pn.widgets.Select(
                name='Affinity', 
                options=self._model.constants.AVAILABLE_AFFINITIES, 
                value=self._model.constants.DEFAULT_AFFINITY,
                sizing_mode=self._STRETCH_WIDTH,
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
            sizing_mode=self._STRETCH_WIDTH
        )
        
        agglomerative_tab = pn.Column(
            pn.Column(
                *[widget for widget in agglomerative_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["agglomerative-input-container"]
            ),
            self._agglomerative_run_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["agglomerative-tab"]
        )
        
        return agglomerative_tab
    
    def _create_spectral_tab(self) -> pn.Column:
        self._spectral_input = {
            "available_norms": pn.widgets.Select(
                name='Available norms', 
                options=self._model.constants.AVAILABLE_NORMS,
                value=self._model.constants.DEFAULT_SELECTED_NORM,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "n_clusters": pn.widgets.IntInput(
                name="Number of Clusters", 
                value=self._model.constants.DEFAULT_NUMBER_OF_CLUSTERS,
                step=1,
                end=100,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "n_init": pn.widgets.IntInput(
                name="Number of Initializations",
                value=self._model.constants.DEFAULT_NUMBER_OF_INIT,
                step=1,
                end=100,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "labels_assign_method": pn.widgets.Select(
                name='Labels Assignment Method',
                options=self._model.constants.AVAILABLE_SPECTRAL_ASSIGN_LABELS,
                value=self._model.constants.DEFAULT_SPECTRAL_ASSIGN_LABELS,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "spectral_affinity_metrics": pn.widgets.Select(
                name='Spectral Affinity Metrics',
                options=self._model.constants.AVAILABLE_SPECTRAL_AFFINITIES,
                value=self._model.constants.DEFAULT_SPECTRAL_AFFINITY,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "n_neighbors": pn.widgets.IntInput(
                name="Number of Neighbors",
                value=self._model.constants.DEFAULT_SPECTRAL_N_NEIGHBORS,
                step=1,
                end=1000,
                sizing_mode=self._STRETCH_WIDTH
            ),
            "gamma": pn.widgets.EditableFloatSlider(
                name="Gamma",
                value=self._model.constants.DEFAULT_SPECTRAL_GAMMA,
                start=self._model.constants.DEFAULT_SPECTRAL_GAMMA,
                step=0.5,
                end=10.0,
                sizing_mode=self._STRETCH_WIDTH,
                margin=(10,18,0,18)
            ),
        }
        
        self._spectral_run_button = pn.widgets.Button(
            name='Run Spectral',
            button_type='success',
            height=55,
            margin=(20,0,10,0),
            sizing_mode=self._STRETCH_WIDTH
        )

        spectral_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._spectral_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["spectral-input-container"]
            ),
            self._spectral_run_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["spectral-tab"]
        )
        
        return spectral_tab
