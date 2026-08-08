import panel as pn

from bokeh.models import Tooltip
from whateels.components import ToggleButton, SimpleDetails
from ..components.nlls_fit_areas_modal import NLLSFitAreasModal
from ..components.nlls_results_view import NLLSResultsView
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...model import FittingModel
    from whateels.components import ModalManager
    from whateels.templates import GeneralPageTemplate


class FittingRightSidebarLayout(pn.Column):
    """Right sidebar of the Fitting page: Manual / Elemental / Results tabs."""

    _STRETCH_WIDTH = 'stretch_width'
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_HEIGHT = 'stretch_height'

    ELEMENT_EAXIS_THRESHOLD = 50
    COMPONENT_EAXIS_THRESHOLD = 4
    COMPONENT_EAXIS_THRESHOLD_VALUE = 50

    _ADJUSTMENTS_SVG = """
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
    _ADJUSTMENTS_ACTIVE_SVG = _ADJUSTMENTS_SVG.replace(
        'stroke="currentColor"', 'stroke="#b63fb5"'
    )
    _FIT_AREAS_MODAL_ID = "Select Area to run fit"

    # --- Anti-overflow style kits -------------------------------------
    # Every Panel/Bokeh layout is a flex container whose children keep `min-width: auto`
    # (bokeh assigns `flex: 1 0 0px` but never `min-width: 0`), so a child can never shrink
    # below its min-content width. Two Bokeh rules make that min-content large:
    #   .bk-input-group { ...; white-space: nowrap; }   (bokeh-widgets.js) -> a widget label
    #                                                    is an unbreakable box
    #   .bk-btn, ::file-selector-button { ...; white-space: nowrap; }  -> so is a button label
    # A pn.Row therefore demands the SUM of its children's labels, which in a 330px sidebar
    # overflows and, because #right-sidebar declares overflow-y:auto (so overflow-x computes
    # to auto), paints a horizontal scrollbar.
    #
    # _ROW_FLUID turns every multi-widget row into a wrapping flex line: the row's floor drops
    # from sum(children) to max(children), so it reflows instead of overflowing.
    # These have to travel as `styles=` / `stylesheets=`: fitting.css is served as a document
    # <link> and never reaches the shadow roots the tab bodies render into.
    _ROW_FLUID = {'display': 'flex', 'flex-wrap': 'wrap', 'min-width': '0'}
    _SHRINKABLE = {'min-width': '0'}
    _SECTION_CONTAINED = {
        'box-sizing': 'border-box',
        'max-width': '100%',
        'min-width': '0',
        'overflow-x': 'hidden',
    }

    @staticmethod
    def _fluid_row_styles(**extra) -> dict:
        """Wrapping-row styles, optionally merged with row-specific declarations."""
        return {**FittingRightSidebarLayout._ROW_FLUID, **extra}

    @staticmethod
    def _left_tooltip_icon(content: str, **params) -> pn.widgets.TooltipIcon:
        """Create a help icon whose popup stays inside the right sidebar viewport."""
        params.setdefault("css_classes", ["tooltip-icon"])
        return pn.widgets.TooltipIcon(
            value=Tooltip(content=content, position="left"),
            **params,
        )

    # Sliders need their own container inside a SimpleDetails (see _in_slider_container).
    _SLIDER_TYPES = (
        pn.widgets.EditableRangeSlider,
        pn.widgets.EditableFloatSlider,
        pn.widgets.EditableIntSlider,
        pn.widgets.RangeSlider,
        pn.widgets.IntRangeSlider,
        pn.widgets.FloatSlider,
        pn.widgets.IntSlider,
        pn.widgets.DiscreteSlider,
    )

    def __init__(
        self,
        model: "FittingModel",
        custom_page: "GeneralPageTemplate | None" = None,
        modal_manager: "ModalManager | None" = None,
    ):
        self._model = model
        self._modal_manager = modal_manager
        constants = model.constants

        self._elemental_fit_areas_modal = NLLSFitAreasModal(
            custom_page,
            title=self._FIT_AREAS_MODAL_ID,
        )
        if modal_manager is not None:
            modal_manager.register_modal(
                self._FIT_AREAS_MODAL_ID,
                self._elemental_fit_areas_modal,
            )

        # --- Shared / root widgets ---------------------------------------
        self._use_preprocessed_data_switch = pn.widgets.Switch(
            name="Use Preprocessed Data",
            value=False,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["background-subtraction-switch"],
        )
        self._fitting_tabs: Optional[pn.Tabs] = None
        self._elemental_results_view = NLLSResultsView()

        # --- Manual tab widgets ------------------------------------------
        self._component_model_input: dict[str, pn.widgets.Widget] = {}

        self._fitting_add_compontent_button = pn.widgets.Button(
            name='Add Component',
            button_type='primary',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
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
            states=states,
            margin=0,
            height=55,
            disabled=False,
            sizing_mode=self._STRETCH_WIDTH,
        )

        self._component_item_view_container = pn.Column(
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["component-container"],
        )

        # --- Elemental tab widgets ---------------------------------------
        self._elemental_input: dict[str, pn.widgets.Widget] = {}

        self._elemental_background_status = pn.pane.Alert(
            constants.ELEMENTAL_BACKGROUND_STATUS_UNKNOWN,
            alert_type='warning',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            css_classes=["elemental-status"],
        )
        self._elemental_geometry_status = pn.pane.Alert(
            constants.ELEMENTAL_GEOMETRY_STATUS_UNKNOWN,
            alert_type='warning',
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            css_classes=["elemental-status"],
        )
        # Read-only: the controller writes the onset resolved from the OOS catalogue.
        self._elemental_onset_readout = pn.widgets.StaticText(
            value=constants.ELEMENTAL_ONSET_READOUT_PLACEHOLDER,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )
        self._elemental_add_edge_button = pn.widgets.Button(
            name='Add Edge',
            button_type='primary',
            height=55,
            margin=(10, 0, 0, 0),
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )
        self._elemental_build_model_button = pn.widgets.Button(
            name='Build Elemental Model',
            button_type='primary',
            height=55,
            margin=(10, 0, 0, 0),
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )
        self._elemental_use_current_clustering_button = (
            self._elemental_fit_areas_modal.use_current_clustering_button
        )
        self._elemental_fit_button = pn.widgets.Button(
            name='Fit',
            button_type='success',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )
        self._elemental_fit_area_settings_button = pn.widgets.ButtonIcon(
            icon=self._ADJUSTMENTS_SVG,
            active_icon=self._ADJUSTMENTS_ACTIVE_SVG,
            size='2em',
            width=55,
            height=55,
            margin=0,
            disabled=True,
            styles={
                "cursor": "pointer",
                "display": "grid",
                "place-items": "center",
                "border-radius": "6px",
            },
        )
        if modal_manager is not None:
            self._elemental_fit_area_settings_button.on_click(
                lambda _: modal_manager.open_modal(self._FIT_AREAS_MODAL_ID)
            )
        self._elemental_run_nlls_button = pn.widgets.Button(
            name='Run Elemental NLLS',
            button_type='success',
            height=55,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            disabled=True,
        )
        self._elemental_cancel_button = pn.widgets.Button(
            name='Cancel',
            button_type='danger',
            height=55,
            margin=0,
            width=110,
            sizing_mode='fixed',
            disabled=True,
        )

        super().__init__(
            self._create_layout(),
            sizing_mode=self._STRETCH_BOTH,
            styles={
                'height': '100%',
                'max-width': '100%',
                'min-height': '0',
                'min-width': '0',
                'overflow': 'hidden',
            },
        )

    def _in_slider_container(self, widget):
        """Wrap sliders so their editors and track stay inside SimpleDetails.

        A Bokeh slider stretches its track to the full available width and lets the handles
        stick out past it, so dropped straight into a SimpleDetails it can overflow the box.
        The Home sidebar never does that: every slider gets its own
        stretch_width column first (`_range_slider_container`, `threshold_slider_container`
        and `window_slider_container` in
        whateels/pages/home/MVC/view/plots/spectrum_image_plot.py). This mirrors that.

        It also relaxes the slider's own editor row. An Editable*Slider is a CompositeWidget
        whose `_composite` is Column[Row[label, FloatInput(min_width=50), '...',
        FloatInput(min_width=50)], slider]; that Row does not wrap, so its two spin boxes plus
        the label are an unbreakable ~200px block. Letting it wrap keeps the whole sidebar
        free of min-content floors. Guarded with getattr: if Panel ever changes the composite
        shape, the layout simply stays as it is today.

        Non-slider widgets are returned untouched.
        """
        if not isinstance(widget, self._SLIDER_TYPES):
            return widget

        widget.margin = 0
        widget.styles = {
            **(widget.styles or {}),
            'box-sizing': 'border-box',
            'max-width': '100%',
            'min-width': '0',
        }

        for child in getattr(widget, '_composite', []) or []:
            if isinstance(child, pn.Row):
                child.styles = {
                    **(child.styles or {}),
                    **self._ROW_FLUID,
                    'box-sizing': 'border-box',
                    'max-width': '100%',
                }

                for sub in getattr(child, 'objects', []) or []:
                    if hasattr(sub, 'styles'):
                        sub.styles = {
                            **(sub.styles or {}),
                            'box-sizing': 'border-box',
                            'min-width': '0',
                            'max-width': '100%',
                        }

                    # Only the numeric editors should consume the remaining row
                    # width. The label and the "..." separator keep their intrinsic
                    # size; stretching them was what pushed the second editor out.
                    if isinstance(sub, (pn.widgets.FloatInput, pn.widgets.IntInput)):
                        sub.min_width = 0
                        sub.width = None
                        sub.sizing_mode = self._STRETCH_WIDTH
            elif isinstance(child, self._SLIDER_TYPES):
                # Let Bokeh subtract these margins from the stretch width. Never add
                # CSS width:100% here: that would restore the exact overflow the
                # margins are intended to prevent.
                child.sizing_mode = self._STRETCH_WIDTH
                child.margin = (0, 10, 5, 10)
                child.styles = {
                    **(child.styles or {}),
                    'box-sizing': 'border-box',
                    'min-width': '0',
                    'max-width': '100%',
                }

        return pn.Column(
            widget,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles={
                **self._SHRINKABLE,
                'box-sizing': 'border-box',
                'max-width': '100%',
            },
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def fitting_tabs(self) -> pn.Tabs:
        """Access the right sidebar tabs widget."""
        return self._fitting_tabs

    @property
    def background_subtraction_switch(self) -> pn.widgets.Switch:
        """Access the 'Use Preprocessed Data' switch."""
        return self._use_preprocessed_data_switch

    @property
    def component_input(self) -> dict[str, pn.widgets.Widget]:
        """Access the Manual tab component input widgets."""
        return self._component_model_input

    @property
    def fitting_add_component_button(self) -> pn.widgets.Button:
        """Access the Manual tab 'Add Component' button."""
        return self._fitting_add_compontent_button

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
    def elemental_background_status(self) -> pn.pane.Alert:
        """Access the Elemental NLLS background status pane."""
        return self._elemental_background_status

    @property
    def elemental_geometry_status(self) -> pn.pane.Alert:
        """Access the Elemental NLLS experimental-geometry status pane."""
        return self._elemental_geometry_status

    @property
    def elemental_onset_readout(self) -> pn.widgets.StaticText:
        """Access the read-only Elemental NLLS edge onset readout."""
        return self._elemental_onset_readout

    @property
    def elemental_add_edge_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Add Edge' button."""
        return self._elemental_add_edge_button

    @property
    def elemental_build_model_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Build Elemental Model' button."""
        return self._elemental_build_model_button

    @property
    def elemental_use_current_clustering_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Use Current Clustering' button."""
        return self._elemental_use_current_clustering_button

    @property
    def elemental_fit_button(self) -> pn.widgets.Button:
        """Access the single Elemental NLLS reference-fit action."""
        return self._elemental_fit_button

    @property
    def elemental_fit_area_settings_button(self) -> pn.widgets.ButtonIcon:
        """Access the clustered-area selection modal trigger."""
        return self._elemental_fit_area_settings_button

    @property
    def elemental_fit_areas_input(self) -> pn.widgets.MultiChoice:
        """Access the area selector hosted inside the fit modal."""
        return self._elemental_fit_areas_modal.area_selector

    @property
    def elemental_select_all_fit_areas_button(self) -> pn.widgets.Button:
        """Access the modal action that selects every cluster."""
        return self._elemental_fit_areas_modal.select_all_button

    @property
    def elemental_run_nlls_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Run Elemental NLLS' button."""
        return self._elemental_run_nlls_button

    @property
    def elemental_cancel_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Cancel' button."""
        return self._elemental_cancel_button

    @property
    def elemental_results_view(self) -> NLLSResultsView:
        """Access the reactive Elemental NLLS reference-results view."""
        return self._elemental_results_view

    # ------------------------------------------------------------------
    # Layout composition
    # ------------------------------------------------------------------
    def _create_layout(self) -> pn.Column:
        """Compose the sidebar root: preprocessed-data switch plus the tab set."""
        constants = self._model.constants

        background_subtraction_label = pn.pane.Markdown(
            "### Use Preprocessed Data",
        )

        is_preprocessed_available = self._model.is_preprocessed_data_available()
        self._use_preprocessed_data_switch.disabled = not is_preprocessed_available

        subtraction_bg_tooltip = (
            "Enable use of Home preprocessed data for fitting."
            if is_preprocessed_available else "Must do some preprocessing first at home page before using this option."
        )
        background_subtraction_container = pn.Row(
            self._left_tooltip_icon(subtraction_bg_tooltip),
            background_subtraction_label,
            self._use_preprocessed_data_switch,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["background-subtraction-container"],
            styles=self._fluid_row_styles(),
        )

        manual_tab = self._create_manual_tab()
        elemental_tab = self._create_elemental_tab()
        results_tab = self._create_results_tab()

        # Tabs render inside Bokeh's shadow root, so align their headers with a
        # component stylesheet instead of the page-level fitting.css file.
        self._fitting_tabs = pn.Tabs(
            (constants.TAB_MANUAL, manual_tab),
            (constants.TAB_ELEMENTAL, elemental_tab),
            (constants.TAB_RESULTS, results_tab),
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["fitting-tabs"],
            stylesheets=["""
                :host {
                    grid-template-columns: minmax(0, 1fr) !important;
                    height: 100% !important;
                    max-width: 100%;
                    min-height: 0;
                    min-width: 0;
                    overflow: hidden;
                }

                .bk-header {
                    justify-content: stretch;
                    min-width: 0;
                    overflow: hidden;
                    width: 100%;
                }

                .bk-tab {
                    flex: 1 1 0;
                    min-width: 0;
                    overflow: hidden;
                    text-align: center;
                    text-overflow: ellipsis;
                }
            """]
        )

        right_sidebar = pn.Column(
            background_subtraction_container,
            pn.Column(
                self._fitting_tabs,
                sizing_mode=self._STRETCH_BOTH,
                styles={
                    'flex': '1 1 0',
                    'height': '100%',
                    'max-width': '100%',
                    'min-height': '0',
                    'min-width': '0',
                    'overflow': 'hidden',
                }
            ),
            styles={
                'display': 'flex',
                'flex': '1 1 0',
                'height': '100%',
                'max-width': '100%',
                'min-height': '0',
                'min-width': '0',
                'overflow': 'hidden',
            },
            sizing_mode=self._STRETCH_BOTH,
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
                css_classes=['my-range'],
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

        details = SimpleDetails(
            title="NLLS Instructions",
            content=pn.Column(
                *[
                    self._in_slider_container(widget)
                    for widget in self._component_model_input.values()
                ],
                self._fitting_add_compontent_button,
                sizing_mode=self._STRETCH_WIDTH
            ),
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0,0,10,0),
            styles=dict(self._SECTION_CONTAINED),
            css_classes=['my-range-container'],
            stylesheets=["""
            :host .my-range,
            :host .my-range * {
                min-width: 0 !important;
                max-width: 100% !important;
                width: auto !important;
                box-sizing: border-box !important;
            }

            :host .my-range .bk-row,
            :host .my-range .bk-input-group,
            :host .my-range .bk-input-wrapper,
            :host .my-range .bk-slider,
            :host .my-range .bk-slider-horizontal,
            :host .my-range .bk-slider-title {
                display: flex !important;
                flex-wrap: wrap !important;
                align-items: center !important;
                justify-content: flex-start !important;
                padding: 0 !important;
                margin: 0 !important;
                min-width: 0 !important;
                max-width: 100% !important;
                width: 100% !important;
                box-sizing: border-box !important;
                white-space: normal !important;
            }

            :host .my-range .bk-input-group .bk-input,
            :host .my-range .bk-input-wrapper .bk-input {
                min-width: 0 !important;
                max-width: 100% !important;
                width: auto !important;
                flex: 1 1 0 !important;
                box-sizing: border-box !important;
            }

            :host .my-range .bk-row > *,
            :host .my-range .bk-row > .bk-input-group,
            :host .my-range .bk-row > .bk-input-wrapper {
                min-width: 0 !important;
                max-width: 100% !important;
                width: 100% !important;
                box-sizing: border-box !important;
            }

            :host .my-range .bk-slider-horizontal .bk-slider-bar,
            :host .my-range .bk-slider-horizontal .bk-slider-range {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 0 !important;
                box-sizing: border-box !important;
            }

            :host .my-range .bk-slider-handle {
                transform: none !important;
            }
            """],
        )

        manual_tab = pn.Column(
            details,
            self._energy_map_toggle_button,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["manual-tab"],
            margin=(15, 0, 0, 0),
            # .manual-tab lives in a shadow root, so fitting.css cannot reach it.
            styles={
                'box-sizing': 'border-box',
                'height': '100%',
                'max-width': '100%',
                'min-width': '0',
                'overflow-x': 'hidden',
                'overflow-y': 'auto',
                'padding': '0 10px',
            },
        )
        return manual_tab

    def _create_elemental_tab(self) -> pn.Column:
        """Build the 'Elemental' tab: OOS-driven model builder sections and action stack.

        The experimental geometry is no longer a section here: E0, beta and alpha are read
        and edited in the shared Dataset Information card at the top of the stack, which
        writes straight into `dataset.attrs`.

        Save/Load Model (NLLS_TODO 5.1:287 and 12.1) are deliberately absent: they will be
        reinstated in the serialization phase, once a real model artifact exists.
        """
        self._elemental_input = {}

        edge_details = self._create_elemental_edge_section()
        model_details = self._create_elemental_model_section()

        elemental_tab = pn.Column(
            # Scrollable section stack. It must stay the PARENT of the SimpleDetails
            # blocks: nesting it inside one would drop its flex/overflow rules.
            pn.Column(
                # Both status panes stay outside the collapsible sections: they gate
                # Add Edge / Build / Run, so a folded warning would hide the blocker.
                self._elemental_background_status,
                self._elemental_geometry_status,
                edge_details,
                model_details,
                sizing_mode=self._STRETCH_BOTH,
                css_classes=["elemental-input-container"],
                # The .elemental-input-container rule in fitting.css is dead (shadow root),
                # so the scroll/clip container has to be declared here. overflow-x:hidden
                # makes THIS the element that absorbs any residual overflow instead of
                # #right-sidebar, which is what used to grow the horizontal scrollbar.
                styles={
                    'flex': '1 1 0',
                    'min-height': '0',
                    'min-width': '0',
                    'overflow-y': 'auto',
                    'overflow-x': 'hidden',
                    'padding': '0.5rem 0',
                },
            ),
            # Action stack, sibling of the scroll container so it stays visible.
            pn.Column(
                pn.Row(
                    self._elemental_fit_button,
                    self._elemental_fit_area_settings_button,
                    margin=0,
                    sizing_mode=self._STRETCH_WIDTH,
                    styles=self._fluid_row_styles(gap='10px'),
                ),
                pn.Row(
                    self._elemental_run_nlls_button,
                    self._elemental_cancel_button,
                    margin=0,
                    sizing_mode=self._STRETCH_WIDTH,
                    styles=self._fluid_row_styles(gap='10px'),
                ),
                margin=0,
                sizing_mode=self._STRETCH_WIDTH,
                css_classes=["elemental-actions"],
                styles={
                    'box-sizing': 'border-box',
                    'flex-shrink': '0',
                    'max-width': '100%',
                    'min-height': '0',
                    'min-width': '0',
                    'overflow-x': 'hidden',
                    'padding': '10px',
                    'gap': '10px',
                },
            ),
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["elemental-tab"],
            margin=0,
            styles={
                'box-sizing': 'border-box',
                'height': '100%',
                'max-width': '100%',
                'min-height': '0',
                'min-width': '0',
                'overflow': 'hidden',
                'padding-top': '15px',
            },
        )

        return elemental_tab

    def _create_elemental_edge_section(self) -> SimpleDetails:
        """Build the 'Edge Definition' section. The onset is derived, never typed in."""
        constants = self._model.constants

        self._elemental_input["element_atomic_number"] = pn.widgets.IntInput(
            name="Element Atomic Number",
            value=constants.DEFAULT_ELEMENTAL_ATOMIC_NUMBER,
            start=constants.ELEMENTAL_MIN_ATOMIC_NUMBER,
            end=constants.ELEMENTAL_MAX_ATOMIC_NUMBER,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )
        # Options come from the OOS catalogue: the controller populates them.
        self._elemental_input["subshells"] = pn.widgets.MultiChoice(
            name="Subshells",
            options=[],
            value=[],
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            disabled=True,
        )
        self._elemental_input["chemical_shift"] = pn.widgets.FloatInput(
            name="Chemical shift (eV)",
            value=constants.DEFAULT_ELEMENTAL_CHEMICAL_SHIFT,
            step=constants.ELEMENTAL_CHEMICAL_SHIFT_STEP,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )

        content = pn.Column(
            self._elemental_input["element_atomic_number"],
            pn.Row(
                self._elemental_input["subshells"],
                self._left_tooltip_icon(constants.TOOLTIP_ELEMENTAL_SUBSHELLS),
                sizing_mode=self._STRETCH_WIDTH,
                styles=self._fluid_row_styles(),
            ),
            pn.Row(
                self._elemental_input["chemical_shift"],
                self._left_tooltip_icon(constants.CHEMICAL_SHIFT_TOOLTIP, width=30),
                sizing_mode=self._STRETCH_WIDTH,
                styles=self._fluid_row_styles(),
            ),
            self._elemental_onset_readout,
            self._elemental_add_edge_button,
            sizing_mode=self._STRETCH_WIDTH,
        )

        return SimpleDetails(
            title=constants.SECTION_ELEMENTAL_EDGE,
            content=content,
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=dict(self._SECTION_CONTAINED),
        )

    def _create_elemental_model_section(self) -> SimpleDetails:
        """Build model composition controls and the reversible clustering action."""
        constants = self._model.constants

        self._elemental_input["model_composition"] = pn.widgets.Select(
            name="Model composition",
            options=constants.AVAILABLE_ELEMENTAL_MODEL_COMPOSITIONS,
            value=constants.DEFAULT_ELEMENTAL_MODEL_COMPOSITION,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )
        self._elemental_input["elnes_shape"] = pn.widgets.Select(
            name="ELNES shape",
            options=constants.AVAILABLE_ELEMENTAL_MODELS,
            value=constants.DEFAULT_ELEMENTAL_MODEL,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )
        self._elemental_input["flexibility"] = pn.widgets.Select(
            name="Flexibility",
            options=constants.AVAILABLE_ELEMENTAL_FLEXIBILITIES,
            value=constants.DEFAULT_ELEMENTAL_FLEXIBILITY,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )
        self._elemental_input["soften_edge"] = pn.widgets.Checkbox(
            name="Soften edge",
            value=constants.DEFAULT_ELEMENTAL_SOFTEN_EDGE,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )
        self._elemental_input["soften_strength"] = pn.widgets.FloatInput(
            name="Soften strength (eV)",
            value=constants.DEFAULT_ELEMENTAL_SOFTEN_STRENGTH,
            start=0.0,
            step=constants.ELEMENTAL_SOFTEN_STRENGTH_STEP,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )

        content = pn.Column(
            self._elemental_input["model_composition"],
            self._elemental_input["elnes_shape"],
            self._elemental_input["flexibility"],
            pn.Row(
                self._elemental_input["soften_edge"],
                self._elemental_input["soften_strength"],
                self._left_tooltip_icon(constants.TOOLTIP_ELEMENTAL_SOFTEN),
                margin=0,
                sizing_mode=self._STRETCH_WIDTH,
                styles=self._fluid_row_styles(gap='10px'),
            ),
            self._elemental_build_model_button,
            sizing_mode=self._STRETCH_WIDTH,
        )

        return SimpleDetails(
            title=constants.SECTION_ELEMENTAL_MODEL,
            content=content,
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=dict(self._SECTION_CONTAINED),
        )

    def _create_results_tab(self) -> pn.Column:
        """Build the scrollable Elemental NLLS reference-results tab."""
        results_tab = pn.Column(
            self._elemental_results_view,
            sizing_mode=self._STRETCH_BOTH,
            css_classes=["results-tab"],
            margin=(15, 0, 0, 0),
            styles={
                'box-sizing': 'border-box',
                'height': '100%',
                'max-width': '100%',
                'min-width': '0',
                'overflow-x': 'hidden',
                'overflow-y': 'auto',
            },
        )
        return results_tab
