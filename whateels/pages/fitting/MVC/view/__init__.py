import panel as pn

from whateels.helpers import CSS_ROOT
from whateels.components import ModalManager, UploadedFile, ToggleButton
from panel.viewable import Viewable
from panel.pane import HTML
from typing import TYPE_CHECKING, Optional

from .layouts import FittingRightSidebarLayout

if TYPE_CHECKING:
    from ..model import FittingModel
    from whateels.templates import GeneralPageTemplate


class FittingView:
    """View layer for fitting page sidebars, controls, and main plotting container."""

    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_HEIGHT = 'stretch_height'

    ELEMENT_EAXIS_THRESHOLD = 50
    COMPONENT_EAXIS_THRESHOLD = 4
    COMPONENT_EAXIS_THRESHOLD_VALUE = 50

    def __init__(
        self,
        model: "FittingModel",
        custom_page: "GeneralPageTemplate | None" = None,
    ):
        self._model = model
        self._custom_page = custom_page
        self._modal_manager = ModalManager(custom_page) if custom_page is not None else None

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

        self._right_sidebar_layout_obj: Optional[FittingRightSidebarLayout] = None

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
    def right_sidebar(self) -> "FittingRightSidebarLayout":
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
    def elemental_run_nlls_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Run Elemental NLLS' button."""
        return self._elemental_run_nlls_button

    @property
    def fitting_tabs(self) -> pn.Tabs:
        """Access the right sidebar tabs widget."""
        return self._fitting_tabs
    @property
    def elemental_add_edge_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Add Edge' button."""
        return self._elemental_add_edge_button
    @property
    def elemental_build_model_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Build Elemental Model' button."""
        return self._elemental_build_model_button
    @property
    def elemental_fit_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS reference-fit button."""
        return self._elemental_fit_button
    @property
    def elemental_fit_area_settings_button(self) -> pn.widgets.ButtonIcon:
        """Access the clustered-area selection modal trigger."""
        return self._elemental_fit_area_settings_button
    @property
    def elemental_fit_areas_input(self) -> pn.widgets.MultiChoice:
        """Access the clustered-area selector hosted by the modal."""
        return self._elemental_fit_areas_input
    @property
    def elemental_select_all_fit_areas_button(self) -> pn.widgets.Button:
        """Access the modal's Select all action."""
        return self._elemental_select_all_fit_areas_button
    @property
    def elemental_cancel_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Cancel' button."""
        return self._elemental_cancel_button
    @property
    def elemental_use_current_clustering_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Use Current Clustering' button."""
        return self._elemental_use_current_clustering_button
    @property
    def elemental_background_status(self) -> pn.pane.Alert:
        """Access the Elemental NLLS background status pane."""
        return self._elemental_background_status
    @property
    def elemental_geometry_status(self) -> pn.pane.Alert:
        """Access the Elemental NLLS experimental-geometry status pane."""
        return self._elemental_geometry_status
    @property
    def elemental_edge_section(self):
        """Access the collapsible Elemental 'Edge Definition' section."""
        return self._elemental_edge_section
    @property
    def elemental_model_section(self):
        """Access the collapsible Elemental 'Model Setup' section."""
        return self._elemental_model_section
    @property
    def elemental_onset_readout(self) -> pn.widgets.StaticText:
        """Access the read-only Elemental NLLS edge onset readout."""
        return self._elemental_onset_readout
    @property
    def elemental_results_view(self):
        """Access the Elemental NLLS reference-results view."""
        return self._elemental_results_view
    @property
    def modals(self) -> list:
        """Return modal components for the page template container."""
        return self._modal_manager.modals if self._modal_manager is not None else []
    @dataset_info.setter
    def dataset_info(self, component: pn.viewable.Viewable):
        """Set the last dataset info component (must be a Panel Viewable)."""
        self._dataset_info_layout = component

    def _init_components(self):
        """Create left/main/right sections for the fitting page."""
        self.left_sidebar = self._left_sidebar_layout()
        self.main = self._main_layout()
        self.right_sidebar = self._right_sidebar_layout()
        self._bind_right_sidebar_widgets()

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
    
    def _right_sidebar_layout(self) -> FittingRightSidebarLayout:
        """Build the right sidebar by delegating to FittingRightSidebarLayout."""
        self._right_sidebar_layout_obj = FittingRightSidebarLayout(
            self._model,
            self._custom_page,
            self._modal_manager,
        )
        return self._right_sidebar_layout_obj

    def _bind_right_sidebar_widgets(self):
        """Re-expose the sidebar widgets under the exact attribute names the
        controller and the layout manager already use. Every alias points at the
        SAME object owned by FittingRightSidebarLayout."""
        layout = self._right_sidebar_layout_obj
        if layout is None:
            raise RuntimeError(
                "FittingView cannot bind the right sidebar widgets: "
                "FittingRightSidebarLayout was not built. _right_sidebar_layout() must run "
                "successfully before _bind_right_sidebar_widgets(); check the traceback of the "
                "sidebar construction instead of the AttributeError raised downstream."
            )

        # Manual tab (the controller reads these private names directly).
        self._component_model_input = layout.component_input
        self._fitting_add_compontent_button = layout.fitting_add_component_button
        self._use_preprocessed_data_switch = layout.background_subtraction_switch
        self._energy_map_toggle_button = layout.energy_map_toggle_button
        self._component_item_view_container = layout.component_item_view_container

        # Elemental tab.
        self._elemental_input = layout.elemental_input
        self._elemental_add_edge_button = layout.elemental_add_edge_button
        self._elemental_build_model_button = layout.elemental_build_model_button
        self._elemental_fit_button = layout.elemental_fit_button
        self._elemental_fit_area_settings_button = layout.elemental_fit_area_settings_button
        self._elemental_fit_areas_input = layout.elemental_fit_areas_input
        self._elemental_select_all_fit_areas_button = layout.elemental_select_all_fit_areas_button
        self._elemental_run_nlls_button = layout.elemental_run_nlls_button
        self._elemental_cancel_button = layout.elemental_cancel_button
        self._elemental_use_current_clustering_button = layout.elemental_use_current_clustering_button
        self._elemental_background_status = layout.elemental_background_status
        self._elemental_geometry_status = layout.elemental_geometry_status
        self._elemental_edge_section = layout.elemental_edge_section
        self._elemental_model_section = layout.elemental_model_section
        self._elemental_onset_readout = layout.elemental_onset_readout
        self._elemental_results_view = layout.elemental_results_view

        self._fitting_tabs = layout.fitting_tabs
