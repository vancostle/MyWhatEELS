from typing import TYPE_CHECKING
from whateels.helpers import HTML_ROOT, CSS_ROOT
from whateels.components import UploadedFile, ErrorPanel
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
        self._error_container_layout = None
        
        # Add any additional, unique setup for ClusteringView below
        self._main_layout()
        self._right_sidebar_layout()
        self._sidebar_layout()

    def _sidebar_layout(self):
        uploaded_file = UploadedFile(filename="uploaded_file.dm4", sizing_mode=self.STRETCH_WIDTH)
        self.sidebar = pn.Column(
            uploaded_file,
            sizing_mode=self.STRETCH_WIDTH
        )
        
        fake_dataset_info = self._create_fake_dataset_info_layout()
        self.sidebar.append(fake_dataset_info)
        
        error_panel = ErrorPanel(sizing_mode=self.STRETCH_WIDTH)
        self.sidebar.append(error_panel)

    def _main_layout(self):
        fake_tabs = pn.Tabs(
            ("EELS 0", pn.pane.Markdown("Content for EELS 0", sizing_mode=self.STRETCH_BOTH)),
            ("EELS 1", pn.pane.Markdown("Content for EELS 1", sizing_mode=self.STRETCH_BOTH)),
            sizing_mode=self.STRETCH_BOTH
        )
        
        self.main = pn.Column(
            fake_tabs,
            sizing_mode=self.STRETCH_BOTH
        )
        return self.main

    def _right_sidebar_layout(self):
        
        pre_normalization_label = pn.pane.Markdown(
            "### Pre-normalization", 
        )
        
        pre_normalization_switch = pn.widgets.Switch(
            name="Pre-normalization", 
            value=False, 
            sizing_mode='stretch_height',
            css_classes=["pre-normalization-switch"]
        )
        pre_normalization_container = pn.Row(
            pre_normalization_label,
            pre_normalization_switch,
            sizing_mode=self.STRETCH_WIDTH
        )
        
        available_norms_select = pn.widgets.Select(name='Available norms', options=['I1', 'I2', 'MAX'])
        
        available_norms_container = pn.Row(
            available_norms_select,
            sizing_mode=self.STRETCH_WIDTH
        )
        
        k_means_tab = pn.pane.Markdown("Clustering controls go here.", sizing_mode=self.STRETCH_WIDTH)
        agglomerative_tab = pn.pane.Markdown("Dimensionality reduction controls go here.", sizing_mode=self.STRETCH_WIDTH)
        spectral_tab = pn.pane.Markdown("Density-based clustering controls go here.", sizing_mode=self.STRETCH_WIDTH)
        
        k_means_tab = pn.Column(
            pn.widgets.IntInput(name="Number of Clusters", value=1, step=1, end=1000, sizing_mode=self.STRETCH_WIDTH),
            pn.widgets.IntInput(name="Number of Initializations", value=1, step=1, end=1000, sizing_mode=self.STRETCH_WIDTH),
            pn.widgets.IntInput(name="Max Iterations", value=300, step=1, end=10000, sizing_mode=self.STRETCH_WIDTH),
            pn.widgets.Select(name='Initialization Method', options=['k-means++', 'random'], sizing_mode=self.STRETCH_WIDTH),
            sizing_mode=self.STRETCH_BOTH
        )
        
        clustering_hub = pn.Tabs(
            ("K-Means", k_means_tab),
            ("Agglomerative", agglomerative_tab),
            ("Spectral", spectral_tab),
            sizing_mode=self.STRETCH_BOTH
        )
        
        buttons_container = pn.Column(
            pn.Row(
                pn.widgets.Button(name="RUN", button_type="success", height=130, sizing_mode=self.STRETCH_WIDTH),
                pn.widgets.Button(name="STORE", button_type="primary", height=130, sizing_mode=self.STRETCH_WIDTH),
                sizing_mode=self.STRETCH_BOTH
            ),
            pn.widgets.Button(name="STOP", button_type="danger", height=40, sizing_mode=self.STRETCH_WIDTH),
            sizing_mode=self.STRETCH_BOTH
        )

        self.right_sidebar = pn.Column(
            pre_normalization_container,
            available_norms_container,
            clustering_hub,
            buttons_container,
            sizing_mode=self.STRETCH_BOTH
        )
        return self.right_sidebar
    
    def _create_fake_dataset_info_layout(self):
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