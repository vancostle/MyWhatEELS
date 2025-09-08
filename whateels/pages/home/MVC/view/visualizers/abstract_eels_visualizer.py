from abc import ABC, abstractmethod
from whateels.helpers import HTML_ROOT
import panel as pn

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model import Model
    from xarray import Dataset

class AbstractEELSVisualizer(ABC):
    """
    Abstract base class for EELS visualizers.
    This class defines the interface for EELS visualizers,
    including methods for creating plots and handling dataset information.
    """
    
    def __init__(self, model: "Model", dataset: "Dataset"):
        super().__init__()

        self._model = model
        self._dataset = dataset

    @abstractmethod
    def create_plots(self):
        """
        Create the main layout for the EELS visualizer.
        
        This method should be implemented by subclasses to define how the plots
        and other UI components are arranged.
        """
        pass

    @abstractmethod
    def create_dataset_info(self):
        # Dataset attribute keys
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        
        # File and encoding constants
        HTML_FILE = 'metadata_info.html'
        READ_MODE = 'r'
        UTF_8 = 'utf-8'
        NOT_AVAILABLE = 'N/A'

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
        
        attrs = self._dataset.attrs if self._dataset is not None else {}

        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)

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
                pn.pane.Str(shape),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_BEAM_ENERGY),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{beam_energy}{ENERGY_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_CONVERGENCE_ANGLE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{convergence_angle}{ANGLE_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Row(
                pn.Row(
                    pn.pane.HTML(LABEL_COLLECTION_ANGLE),
                    sizing_mode=STRETCH_WIDTH
                ),
                pn.pane.Str(f"{collection_angle}{ANGLE_UNIT}"),
                sizing_mode=STRETCH_WIDTH
            ),
            pn.Spacer(height=SPACER_HEIGHT_MEDIUM),
            sizing_mode=STRETCH_WIDTH,
            css_classes=DATASET_INFO_CLASS
        )
        return dataset_info