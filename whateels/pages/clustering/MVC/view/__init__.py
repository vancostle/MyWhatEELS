from typing import TYPE_CHECKING
from whateels.helpers import HTML_ROOT, LoadCSS, CSS_ROOT
from whateels.components import UploadedFile
import panel as pn

if TYPE_CHECKING:
    from ..model import Model

class View:
    
    _STRETCH_WIDTH = "stretch_width"
    _STRETCH_BOTH = "stretch_both"

    # --- Initialization ---
    def __init__(self, model: "Model"):
        self._model = model
        
        self._main_container_layout = None
        self._sidebar_container_layout = None
        self._right_sidebar_container_layout = None
        self._error_container_layout = None

        DATASET_INFO_CSS = str(CSS_ROOT / "dataset_info.css")
        LoadCSS([DATASET_INFO_CSS])  # CSS for the dataset info component

        self._init_visualization_components()

    # --- Properties ---

    @property
    def sidebar(self) -> pn.viewable.Viewable:
        """Sidebar layout containing the file dropper and additional controls."""
        return self._sidebar_container_layout
    
    @property
    def right_sidebar(self) -> pn.Column:
        """Right sidebar layout for additional controls or information."""
        return self._right_sidebar_container_layout

    @property
    def error(self) -> pn.Column:
        """Error layout for displaying error messages."""
        return self._error_container_layout

    @property
    def main(self) -> pn.Column:
        """Main content area layout for displaying plots or placeholders."""
        return self._main_container_layout

    @property
    def error_placeholder(self) -> pn.pane.HTML:
        """HTML placeholder shown when an error occurs."""
        return self._error_placeholder
    
    @property
    def dataset_info(self) -> pn.viewable.Viewable:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout

    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable or None)."""
        if component is not None and not isinstance(component, pn.viewable.Viewable):
            raise ValueError("Component must be a Panel Viewable")
        self._dataset_info_layout = component

    # --- Private/Internal Setup Methods ---

    def _init_visualization_components(self):
        self._sidebar_container_layout = self._sidebar_layout()
        self._main_container_layout = self._main_layout()
        self._right_sidebar_container_layout = self._right_sidebar_layout()
        self._error_container_layout = self._error_layout()

    def _sidebar_layout(self):
        uploaded_file = UploadedFile(
            filename="STEM SI iwjediwedjwwid.dm4",
            sizing_mode=self._STRETCH_WIDTH
        )
        
        
        self._sidebar_container_layout = pn.Column(
            uploaded_file,
            pn.layout.Divider(),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        
        fake_dataset_info = self._create_fake_dataset_info_layout()
        
        self._sidebar_container_layout.append(
            fake_dataset_info
        )
        return self._sidebar_container_layout

    def _main_layout(self):
        self._main_container_layout = pn.Column(
            pn.pane.Markdown("### Clustering Analysis", sizing_mode=self._STRETCH_WIDTH),
            sizing_mode=self._STRETCH_BOTH
        )
        return self._main_container_layout
    
    def _right_sidebar_layout(self):
        self._right_sidebar_container_layout = pn.Column(
            pn.pane.Markdown("### Additional Info", sizing_mode=self._STRETCH_WIDTH),
            sizing_mode=self._STRETCH_WIDTH
        )
        return self._right_sidebar_container_layout
    
    def _error_layout(self):
        self._error_placeholder = pn.pane.HTML(
            "<h3 style='color:red;'>An error occurred while loading the data.</h3>",
            sizing_mode=self._STRETCH_WIDTH
        )
        self._error_container_layout = pn.Column(
            self._error_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )
        return self._error_container_layout
    
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