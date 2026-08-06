import panel as pn

from whateels.helpers import CSS_ROOT
from whateels.components import UploadedFile, ToggleButton, SimpleDetails
from panel.viewable import Viewable
from panel.pane import HTML
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..model import FittingModel


class FittingView:
    """View layer for fitting page sidebars, controls, and main plotting container."""

    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_HEIGHT = 'stretch_height'

    ELEMENT_EAXIS_THRESHOLD = 50
    COMPONENT_EAXIS_THRESHOLD = 4
    COMPONENT_EAXIS_THRESHOLD_VALUE = 50

    def __init__(self, model: "FittingModel"):
        self._model = model

        # Register page CSS once to avoid cross-document stylesheet ownership errors.
        fitting_css = '/assets/css/fitting.css'
        if fitting_css not in pn.config.css_files: # type: ignore
            pn.config.css_files.append(fitting_css) # type: ignore

        # Placeholder
        self._no_file_placeholder = pn.Column(
            HTML(model.placeholders.NO_FILE_LOADED, sizing_mode=self._STRETCH_BOTH),
            sizing_mode=self._STRETCH_BOTH,
        )

        # Layout containers
        self._main = pn.Column(self._no_file_placeholder, sizing_mode=self._STRETCH_BOTH)
        self._left_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._right_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)

        self._error_container_layout = None
        self._dataset_info_layout: Optional[pn.viewable.Viewable] = None

        self._fitting_add_compontent_button = pn.widgets.Button()
        self._component_model_input: dict[str, pn.widgets.Widget] = {}
        self._use_preprocessed_data_switch: pn.widgets.Switch = pn.widgets.Switch()

        self._elemental_input: dict[str, pn.widgets.Widget] = {}
        self._elemental_add_component_button = pn.widgets.Button()
        self._elemental_fit_references_button = pn.widgets.Button()
        self._elemental_run_nlls_button = pn.widgets.Button()
        self._elemental_save_model_button = pn.widgets.FileDownload()

        self._init_components()

    @property
    def main(self) -> pn.Column:
        return self._main
    @main.setter
    def main(self, value: pn.Column):
        self._main = value
    @main.deleter
    def main(self):
        self._main.clear()

    @property
    def left_sidebar(self) -> pn.Column:
        return self._left_sidebar
    @left_sidebar.setter
    def left_sidebar(self, value: pn.Column):
        self._left_sidebar = value
    @left_sidebar.deleter
    def left_sidebar(self):
        self._left_sidebar.clear()

    @property
    def right_sidebar(self) -> pn.Column:
        return self._right_sidebar
    @right_sidebar.setter
    def right_sidebar(self, value: pn.Column):
        self._right_sidebar = value
    @right_sidebar.deleter
    def right_sidebar(self):
        self._right_sidebar.clear()

    @property
    def dataset_info(self) -> Optional[pn.viewable.Viewable]:
        """Reference to the last dataset info component added to the sidebar."""
        return self._dataset_info_layout

    @property
    def no_file_placeholder(self) -> pn.viewable.Viewable:
        """Access the 'no file loaded' placeholder shown in main when no dataset is selected."""
        return self._no_file_placeholder

    @property
    def component_input(self) -> dict[str, pn.widgets.Widget]:
        """Access fitting component input widgets."""
        return self._component_model_input
    @property
    def fitting_add_component_button(self) -> pn.widgets.Button:
        """Access the 'Add Component' fitting button."""
        return self._fitting_add_compontent_button
    
    @property
    def background_subtraction_switch(self) -> pn.widgets.Switch:
        """Access the background subtraction switch."""
        return self._use_preprocessed_data_switch
    
    @property
    def energy_map_toggle_button(self) -> ToggleButton:
        """Access the energy map toggle button."""
        return self._energy_map_toggle_button
    
    @property
    def component_item_view_container(self) -> pn.Column:
        """Access the container for component item views."""
        return self._component_item_view_container

    @property
    def elemental_input(self) -> dict[str, pn.widgets.Widget]:
        """Access the Elemental NLLS input widgets."""
        return self._elemental_input
    @property
    def elemental_add_component_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Add Component' button."""
        return self._elemental_add_component_button
    @property
    def elemental_fit_references_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Fit References' button."""
        return self._elemental_fit_references_button
    @property
    def elemental_run_nlls_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Run Elemental NLLS' button."""
        return self._elemental_run_nlls_button
    @property
    def elemental_save_model_button(self) -> pn.widgets.FileDownload:
        """Access the Elemental NLLS 'Save Current Model' button."""
        return self._elemental_save_model_button


    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component

    def _init_components(self):
        """Create left/main/right sections for the fitting page."""
        self.left_sidebar = self._left_sidebar_layout()
        self.main = self._main_layout()
        self.right_sidebar = self._right_sidebar_layout()

    def _left_sidebar_layout(self):
        """Build the left sidebar with uploaded-file summary and dataset info slot."""
        
        uploaded_file = UploadedFile(
            filename=str(self._model.get_uploaded_filename()), 
            sizing_mode=self._STRETCH_WIDTH, 
            margin=(0,0,10,0)
        )
 
        left_sidebar_container_layout = pn.Column(
            uploaded_file,
            pn.layout.Divider(),
            pn.Spacer(height=10),
            sizing_mode=self._STRETCH_WIDTH
        )
        return left_sidebar_container_layout


    def _main_layout(self):
        """Build the main plotting container initialized with no-file placeholder."""
        self._main_container_layout = pn.Column(
            self._no_file_placeholder,
            sizing_mode=self._STRETCH_BOTH
        )

        return self._main_container_layout
    
    def _right_sidebar_layout(self) -> pn.Column:
        """Build right sidebar controls for component definition and fitting actions."""

        background_subtraction_label = pn.pane.Markdown(
            "### Use Preprocessed Data",
        )

        self._use_preprocessed_data_switch = pn.widgets.Switch(
            name="Use Preprocessed Data",
            value=False,
            sizing_mode='stretch_both',
            css_classes=["background-subtraction-switch"]
        )

        is_preprocessed_available = self._model.is_preprocessed_data_available()
        self._use_preprocessed_data_switch.disabled = not is_preprocessed_available

        subtraction_bg_tooltip = (
            "Enable use of Home preprocessed data for fitting."
            if is_preprocessed_available else "Must do some preprocessing first at home page before using this option."
        )
        background_subtraction_container = pn.Row(
            pn.widgets.TooltipIcon(
                value=subtraction_bg_tooltip,
                css_classes=["tooltip-icon"]
            ),
            background_subtraction_label,
            self._use_preprocessed_data_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-subtraction-container"]
        )

        manual_tab = self._create_manual_tab()
        elemental_tab = self._create_elemental_tab()
        results_tab = self._create_results_tab()

        constants = self._model.constants
        # Tabs render inside Bokeh's shadow root, so align their headers with a
        # component stylesheet instead of the page-level fitting.css file.
        fitting_tabs = pn.Tabs(
            (constants.TAB_MANUAL, manual_tab),
            (constants.TAB_ELEMENTAL, elemental_tab),
            (constants.TAB_RESULTS, results_tab),
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["fitting-tabs"],
            stylesheets=["""
                .bk-header {
                    width: 100%;
                }

                .bk-tab {
                    flex: 1 1 0;
                    text-align: center;
                }
            """]
        )

        right_sidebar = pn.Column(
            background_subtraction_container,
            pn.Column(
                fitting_tabs,
                sizing_mode=self._STRETCH_BOTH,
                styles={'flex': '1'}
            ),
            styles={'display': 'flex'},
            sizing_mode=self._STRETCH_WIDTH,
        )
        return right_sidebar

    def _create_manual_tab(self) -> pn.Column:
        """Build the 'Manual' tab: component creation controls and Show Energy Map."""

        # Component creation controls.
        self._component_model_input = {
            "energy_center": pn.widgets.IntInput(
                name='Energy Center',
                sizing_mode=self._STRETCH_WIDTH,
                value=500,
                start=1,
                end=10000,
                margin=(0,0,10,0),
            ),
            "model_select": pn.widgets.Select(
                name="Select Model",
                options=["GaussianModel",
                        "LorentzianModel",
                        "PseudoVoigtModel",
                        "SplitLorentzianModel"
                        ],
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0,0,10,0)
            ),
            "energy_range": pn.widgets.EditableRangeSlider(
                name='Energy Range',
                sizing_mode=self._STRETCH_WIDTH,
                value=  (540 - self.COMPONENT_EAXIS_THRESHOLD_VALUE, 540 + self.COMPONENT_EAXIS_THRESHOLD_VALUE),
                start=540 - self.COMPONENT_EAXIS_THRESHOLD,
                end=540 + self.COMPONENT_EAXIS_THRESHOLD,
                margin=(0,0,10,0),
            ),
            "flexibility": pn.widgets.Select(
                name="Flexibility",
                options=["Low", "Medium", "High", "Maximum"],
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0,0,10,0)
            )
        }

        self._fitting_add_compontent_button = pn.widgets.Button(
            name='Add Component',
            button_type='primary',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )

        details = SimpleDetails(
            title="NLLS Instructions",
            content=pn.Column(
                *[widget for widget in self._component_model_input.values()],
                self._fitting_add_compontent_button,
                sizing_mode=self._STRETCH_WIDTH
            ),
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0,0,10,0)
        )

        # Toggle button state identifiers.
        _ON = 'on'
        _OFF = 'off'

        # Dictionary keys used by ToggleButton state schema.
        _NAME = 'label'
        _ON_CLICK = 'on_click'
        _BUTTON_TYPE = 'button_type'

        states = {
            _ON: {_NAME: "Hide Energy Map", _ON_CLICK: (lambda: print("Off clicked")), _BUTTON_TYPE: 'primary'},
            _OFF: {_NAME: "Show Energy Map", _ON_CLICK: (lambda: print("On clicked")), _BUTTON_TYPE: 'success'}
        }

        self._energy_map_toggle_button = ToggleButton(
            states = states,
            margin=0,
            height=55,
            disabled=False,
            sizing_mode=self._STRETCH_WIDTH
        )

        self._component_item_view_container = pn.Column(sizing_mode=self._STRETCH_BOTH,
                                                        css_classes=["component-container"])

        manual_tab = pn.Column(
            details,
            self._energy_map_toggle_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["manual-tab"]
        )
        return manual_tab

    def _create_elemental_tab(self) -> pn.Column:
        """Build the 'Elemental' tab: Elemental NLLS model builder controls and action buttons."""
        constants = self._model.constants

        self._elemental_input = {
            "model_select": pn.widgets.Select(
                name="Available model",
                options=constants.AVAILABLE_ELEMENTAL_MODELS,
                value=constants.DEFAULT_ELEMENTAL_MODEL,
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0,0,10,0)
            ),
            "energy_center": pn.widgets.IntInput(
                name='Energy Center',
                sizing_mode=self._STRETCH_WIDTH,
                value=constants.DEFAULT_ELEMENTAL_ENERGY_CENTER,
                start=1,
                end=10000,
                margin=(0,0,10,0),
            ),
            "energy_range": pn.widgets.EditableRangeSlider(
                name='Energy Range (eV)',
                sizing_mode=self._STRETCH_WIDTH,
                value=(
                    constants.DEFAULT_ELEMENTAL_ENERGY_CENTER - constants.ELEMENTAL_ENERGY_RANGE_THRESHOLD,
                    constants.DEFAULT_ELEMENTAL_ENERGY_CENTER + constants.ELEMENTAL_ENERGY_RANGE_THRESHOLD,
                ),
                start=constants.DEFAULT_ELEMENTAL_ENERGY_CENTER - constants.ELEMENTAL_ENERGY_RANGE_THRESHOLD,
                end=constants.DEFAULT_ELEMENTAL_ENERGY_CENTER + constants.ELEMENTAL_ENERGY_RANGE_THRESHOLD,
                margin=(0,0,10,0),
            ),
            "flexibility": pn.widgets.Select(
                name="Flexibility",
                options=constants.AVAILABLE_ELEMENTAL_FLEXIBILITIES,
                value=constants.DEFAULT_ELEMENTAL_FLEXIBILITY,
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0,0,10,0)
            ),
            "area": pn.widgets.Select(
                name="Area",
                options=constants.AVAILABLE_ELEMENTAL_AREAS,
                value=constants.DEFAULT_ELEMENTAL_AREA,
                sizing_mode=self._STRETCH_WIDTH,
                margin=(0,0,10,0)
            ),
        }

        self._elemental_add_component_button = pn.widgets.Button(
            name='Add Component',
            button_type='primary',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )

        self._elemental_fit_references_button = pn.widgets.Button(
            name='Fit References',
            button_type='success',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._elemental_run_nlls_button = pn.widgets.Button(
            name='Run Elemental NLLS',
            button_type='success',
            height=55,
            margin=(10,0,0,0),
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._elemental_save_model_button = pn.widgets.FileDownload(
            label="Save Current Model",
            button_type="primary",
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10,0,0,0),
            icon="download",
            icon_size="20px",
            disabled=True,
        )

        elemental_tab = pn.Column(
            pn.Column(
                *[widget for widget in self._elemental_input.values()],
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["elemental-input-container"]
            ),
            self._elemental_add_component_button,
            self._elemental_fit_references_button,
            self._elemental_run_nlls_button,
            self._elemental_save_model_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["elemental-tab"]
        )

        return elemental_tab

    def _create_results_tab(self) -> pn.Column:
        """Build the 'Results' tab. Placeholder pending Elemental NLLS results implementation."""
        results_tab = pn.Column(
            pn.pane.Markdown("Elemental NLLS results will be shown here once available."),
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["results-tab"]
        )
        return results_tab
