import os

import panel as pn

from bokeh.models import Tooltip
from whateels.components import PeriodicTableOfElementsModal, SimpleDetails, ToggleButton
from ..components.nlls_fit_areas_modal import NLLSFitAreasModal
from ..components.nlls_multifit_controls import NLLSMultifitControls
from ..components.nlls_results_view import NLLSResultsView
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ...model import FittingModel
    from whateels.components import ModalManager
    from whateels.templates import GeneralPageTemplate


class EdgeAddedModal(pn.Column):
    """Live editor for the saved elemental edges in the active NLLS workspace."""

    def __init__(
        self,
        custom_page: "GeneralPageTemplate",
        model: "FittingModel",
        title: str = "Edges Added",
        on_close=None,
        **kwargs,
    ):
        self._custom_page = custom_page
        self._model = model
        self._title = title
        self._on_close = on_close
        self._change_callback = None
        self._editable = True

        self._close_button = pn.widgets.Button(
            name="Okay.",
            button_type="primary",
            sizing_mode="stretch_width",
            margin=0,
        )
        self._close_button.on_click(self._close)

        self._title_pane = pn.pane.Markdown(
            f"## {self._title}",
            margin=0,
            styles={"padding": "0"},
        )

        self._body = pn.Column(
            sizing_mode="stretch_width",
            styles={"min-width": "0", "max-width": "100%"},
        )

        super().__init__(
            self._title_pane,
            pn.Spacer(height=10),
            self._body,
            pn.Spacer(height=10),
            self._close_button,
            sizing_mode="stretch_both",
            styles={
                "padding": "12px 20px 20px",
                "background": "rgba(255,255,255,0.98)",
                "maxWidth": "30vw",
                "minWidth": "220px",
                "maxHeight": "40vh",
                "overflow": "auto",
                "overflow-x": "hidden",
                "boxShadow": "0 0 32px 8px #0002",
            },
            **kwargs,
        )
        self.refresh()

    def set_change_callback(self, callback) -> None:
        self._change_callback = callback

    def set_editable(self, editable: bool) -> None:
        """Enable or lock edits while a frozen NLLS run owns the workspace."""
        editable = bool(editable)
        if self._editable == editable:
            return
        self._editable = editable
        self.refresh()

    def _emit_change(self) -> None:
        if self._change_callback is not None:
            try:
                self._change_callback()
            except Exception:
                pass

    def _edge_entries(self):
        workspace = getattr(self._model.app_state, "nlls_workspace", None)
        if workspace is None or "default" not in workspace.areas:
            return [pn.pane.Markdown("No edges added.", styles={"padding": "12px", "color": "#374151"})]

        area = workspace.areas["default"]
        if not area.continuum_specs:
            return [pn.pane.Markdown("No edges added.", styles={"padding": "12px", "color": "#374151"})]

        entries = []
        for continuum in area.continuum_specs:
            edge_label = f"{continuum.symbol} {'+'.join(continuum.shells)}"
            shift_input = pn.widgets.FloatInput(
                value=float(continuum.chemical_shift.value),
                start=float(continuum.chemical_shift.minimum),
                end=float(continuum.chemical_shift.maximum),
                step=0.1,
                width=100,
                min_width=0,
                max_width=100,
                margin=(0, 0, 0, 0),
                visible=True,
                disabled=not self._editable,
                styles={
                    "min-width": "0",
                    "max-width": "100%",
                    "box-sizing": "border-box",
                },
            )

            def _shift_changed(
                event,
                continuum_id=continuum.id,
                saved_shift=float(continuum.chemical_shift.value),
            ):
                if not self._editable:
                    return
                workspace = getattr(self._model.app_state, "nlls_workspace", None)
                if workspace is None:
                    return
                persisted_shift = saved_shift
                try:
                    persisted_shift = next(
                        (
                            float(item.chemical_shift.value)
                            for item in workspace.areas["default"].continuum_specs
                            if item.id == continuum_id
                        ),
                        saved_shift,
                    )
                    previous_revision = workspace.dirty_revision
                    workspace.set_continuum_chemical_shift(
                        "default", (continuum_id,), float(event.new)
                    )
                    if workspace.dirty_revision == previous_revision:
                        return
                    workspace.refresh_clustering_from_template()
                    self._emit_change()
                except (TypeError, ValueError):
                    # Keep the visible input synchronized with the persisted value
                    # when Panel receives a value outside the ParameterSpec bounds.
                    if event.obj.value != persisted_shift:
                        event.obj.value = persisted_shift

            shift_input.param.watch(_shift_changed, "value")

            delete_button = pn.widgets.Button(
                name="Delete",
                button_type="danger",
                width=110,
                margin=(0, 0, 0, 0),
                disabled=not self._editable,
                styles={
                    "background": "#d65b5b",
                    "color": "#fff",
                    "font-weight": "600",
                    "border-radius": "6px",
                },
            )

            def _delete_edge(_event, edge_id=continuum.edge_id):
                if not self._editable:
                    return
                workspace = getattr(self._model.app_state, "nlls_workspace", None)
                if workspace is None:
                    return
                try:
                    previous_revision = workspace.dirty_revision
                    workspace.remove_edge("default", edge_id)
                    if workspace.dirty_revision == previous_revision:
                        return
                    workspace.refresh_clustering_from_template()
                    self.refresh()
                    self._emit_change()
                except (TypeError, ValueError):
                    pass

            delete_button.on_click(_delete_edge)

            toggle_button = ToggleButton(
                initial_state=True,
                states={
                    "on": {
                        "label": "▲ " + edge_label,
                        "on_click": (),
                        "button_type": "default",
                        "color": "#ca4bc8",
                        "text_color": "#ffffff",
                    },
                    "off": {
                        "label": "▼ " + edge_label,
                        "on_click": (),
                        "button_type": "default",
                        "color": "#7373da",
                        "text_color": "#ffffff",
                    },
                },
                sizing_mode="stretch_width",
                margin=(0, 0, 0, 0),
            )

            details_row = pn.Row(
                pn.widgets.StaticText(value="Chemical Shift (eV)", width=120),
                pn.Spacer(sizing_mode="stretch_width", min_width=0),
                shift_input,
                sizing_mode="stretch_width",
                styles={
                    "align-items": "center",
                    "gap": "12px",
                    "margin": "0",
                    "min-width": "0",
                    "max-width": "100%",
                    "overflow": "hidden",
                },
            )

            actions_row = pn.Row(
                toggle_button,
                delete_button,
                sizing_mode="stretch_width",
                styles={
                    "align-items": "center",
                    "gap": "8px",
                    "margin": "0 0 8px 0",
                },
            )
            card = pn.Column(
                actions_row,
                details_row,
                sizing_mode="stretch_width",
                margin=(0, 0, 12, 0),
                styles={
                    "padding": "0 0 10px 0",
                    "border-radius": "4px",
                    "box-shadow": "0 0 5px #d8d8d8",
                    "background-color": "#f7f7f7",
                    "overflow": "hidden",
                    "max-width": "100%",
                    "min-width": "0",
                },
            )

            def _toggle_fields(
                event,
                toggle=toggle_button,
                details=details_row,
                actions=actions_row,
                entry=card,
            ):
                expanded = toggle.is_on()
                details.visible = expanded
                actions.styles = {
                    **actions.styles,
                    "margin": "0 0 8px 0" if expanded else "0",
                }
                entry.styles = {
                    **entry.styles,
                    "padding": "0 0 10px 0" if expanded else "0",
                }

            toggle_button.on_click(_toggle_fields)
            entries.append(card)
        return entries

    def refresh(self) -> None:
        self._body.objects = self._edge_entries()

    def _close(self, *_):
        self.visible = False
        if self._on_close:
            self._on_close()
        self._custom_page.close_modal()


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
    _PERIODIC_TABLE_MODAL_ID = "Periodic Table of Elements"
    _EDGE_ADDED_MODAL_ID = "Edges Added"
    _EDGE_ADDED_SVG = """
    <svg width="215px" height="215px" viewBox="0 0 26 24" fill="none" xmlns="http://www.w3.org/2000/svg" stroke="#000000" stroke-width="0.00024000000000000003"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round" stroke="#CCCCCC" stroke-width="0.288"></g><g id="SVGRepo_iconCarrier" transform="translate(3.5,0)"> <path d="M3 20C2.44772 20 2 20.4477 2 21C2 21.5523 2.44772 22 3 22V20ZM21 22C21.5523 22 22 21.5523 22 21C22 20.4477 21.5523 20 21 20V22ZM7 17C6.44772 17 6 17.4477 6 18C6 18.5523 6.44772 19 7 19V17ZM14 19C14.5523 19 15 18.5523 15 18C15 17.4477 14.5523 17 14 17V19ZM9 14C8.44772 14 8 14.4477 8 15C8 15.5523 8.44772 16 9 16V14ZM12 16C12.5523 16 13 15.5523 13 15C13 14.4477 12.5523 14 12 14V16ZM8 5V4C7.44772 4 7 4.44772 7 5H8ZM13 5H14C14 4.44772 13.5523 4 13 4V5ZM13 12V13C13.5523 13 14 12.5523 14 12H13ZM8 12H7C7 12.5523 7.44772 13 8 13V12ZM9 5V6C9.45887 6 9.85885 5.6877 9.97014 5.24254L9 5ZM11.5 3L12.4701 2.75746C12.3589 2.3123 11.9589 2 11.5 2V3ZM9.5 3V2C9.04113 2 8.64115 2.3123 8.52986 2.75746L9.5 3ZM12 5L11.0299 5.24254C11.1411 5.6877 11.5411 6 12 6V5ZM13 7C12.4477 7 12 7.44772 12 8C12 8.55228 12.4477 9 13 9V7ZM16.0915 20.1435C15.6184 20.4285 15.466 21.0431 15.7511 21.5161C16.0361 21.9892 16.6506 22.1416 17.1237 21.8565L16.0915 20.1435ZM3 22H21V20H3V22ZM7 19H14V17H7V19ZM9 16H12V14H9V16ZM12 5V12H14V5H12ZM13 11H8V13H13V11ZM9 12V5H7V12H9ZM8 6H9V4H8V6ZM9.97014 5.24254L10.4701 3.24254L8.52986 2.75746L8.02986 4.75746L9.97014 5.24254ZM9.5 4H11.5V2H9.5V4ZM10.5299 3.24254L11.0299 5.24254L12.9701 4.75746L12.4701 2.75746L10.5299 3.24254ZM12 6H13V4H12V6ZM13 9C16.3137 9 19 11.6863 19 15H21C21 10.5817 17.4183 7 13 7V9ZM19 15C19 17.1814 17.8365 19.092 16.0915 20.1435L17.1237 21.8565C19.4443 20.4582 21 17.9113 21 15H19Z" fill="#000000"></path> </g></svg>
    """
    _EDGE_ADDED_ACTIVE_SVG = _EDGE_ADDED_SVG.replace('#000000', '#b63fb5')
    _PERIODIC_TABLE_SVG = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="2" width="20" height="20" rx="2"/>
          <text x="5" y="8" font-size="4.5" font-family="Arial,sans-serif" fill="currentColor" stroke="none">Z</text>
          <text x="12" y="16" text-anchor="middle" font-size="11" font-family="Arial,sans-serif" fill="currentColor" stroke="none" font-weight="bold">E</text>
          <text x="12" y="21" text-anchor="middle" font-size="3" font-family="Arial,sans-serif" fill="currentColor" stroke="none">Element</text>
        </svg>
    """
    _PERIODIC_TABLE_ACTIVE_SVG = """
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" stroke-width="1.5">
          <rect x="2" y="2" width="20" height="20" rx="2"/>
          <text x="5" y="8" font-size="4.5" font-family="Arial,sans-serif" fill="white" stroke="none">Z</text>
          <text x="12" y="16" text-anchor="middle" font-size="11" font-family="Arial,sans-serif" fill="white" stroke="none" font-weight="bold">E</text>
          <text x="12" y="20.5" text-anchor="middle" font-size="3" font-family="Arial,sans-serif" fill="white" stroke="none">Element</text>
        </svg>
    """

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
        # Keep the card width constrained without turning it into a clipping
        # ancestor. MultiChoice renders its options outside the widget bounds.
        'overflow': 'visible',
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

    def _open_periodic_table(self, _=None) -> None:
        """Open the shared periodic-table reference modal when mounted in a page."""
        if self._modal_manager is not None and self._periodic_table_modal is not None:
            self._modal_manager.open_modal(self._PERIODIC_TABLE_MODAL_ID)

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
        self._custom_page = custom_page
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
        self._periodic_table_modal = None
        if custom_page is not None and modal_manager is not None:
            self._periodic_table_modal = PeriodicTableOfElementsModal(custom_page)
            modal_manager.register_modal(
                self._PERIODIC_TABLE_MODAL_ID,
                self._periodic_table_modal,
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
        self._elemental_multifit_controls = NLLSMultifitControls(
            custom_page=custom_page,
            modal_manager=modal_manager,
        )

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
            margin=0,
            sizing_mode='stretch_both',
            disabled=True,
        )
        self._elemental_edges_added_button = pn.widgets.ButtonIcon(
            icon=self._EDGE_ADDED_SVG,
            active_icon=self._EDGE_ADDED_ACTIVE_SVG,
            value=False,
            size='2.2em',
            # 50px (not 55) so the glyph lands on the same vertical axis as the 3em
            # periodic-table icon above: the icon is centred in this box together with
            # the empty .bk-IconLabel and its 5px margin, which pulls it 2.5px left.
            # The 5px freed here goes to the Add Edge button (flex: 1 0 0px).
            width=50,
            height=55,
            margin=(0, 0, 0, 0), 
            disabled=False,
            styles={
                "cursor": "pointer",
                "display": "grid",
                "place-items": "center",
                "border-radius": "6px",
            },
        )
        if self._modal_manager is not None:
            def _open_edges_added_modal(_):
                self._elemental_edges_added_button.value = True
                self._edge_added_modal.refresh()
                self._modal_manager.open_modal(self._EDGE_ADDED_MODAL_ID)

            self._elemental_edges_added_button.on_click(_open_edges_added_modal)
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
        self._elemental_run_progress = pn.indicators.Progress(
            name="Elemental NLLS progress",
            value=0,
            max=100,
            active=False,
            bar_color="success",
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            visible=False,
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
    def elemental_periodic_table_button(self) -> pn.widgets.ButtonIcon:
        """Access the periodic-table modal trigger."""
        return self._elemental_periodic_table_button

    @property
    def periodic_table_modal(self) -> PeriodicTableOfElementsModal | None:
        """Access the shared periodic-table modal when a page owns one."""
        return self._periodic_table_modal

    @property
    def elemental_background_status(self) -> pn.pane.Alert:
        """Access the Elemental NLLS background status pane."""
        return self._elemental_background_status

    @property
    def elemental_geometry_status(self) -> pn.pane.Alert:
        """Access the Elemental NLLS experimental-geometry status pane."""
        return self._elemental_geometry_status

    @property
    def elemental_edge_section(self) -> SimpleDetails:
        """Access the collapsible 'Edge Definition' section."""
        return self._elemental_edge_section

    @property
    def elemental_model_section(self) -> SimpleDetails:
        """Access the collapsible 'Model Setup' section."""
        return self._elemental_model_section

    @property
    def elemental_onset_readout(self) -> pn.widgets.StaticText:
        """Access the read-only Elemental NLLS edge onset readout."""
        return self._elemental_onset_readout

    @property
    def elemental_add_edge_button(self) -> pn.widgets.Button:
        """Access the Elemental NLLS 'Add Edge' button."""
        return self._elemental_add_edge_button

    @property
    def elemental_edges_added_button(self) -> pn.widgets.ButtonIcon:
        """Access the Edge Definition info button for the modal."""
        return self._elemental_edges_added_button

    @property
    def edge_added_modal(self):
        """Access the live modal used to edit saved elemental edges."""
        return self._edge_added_modal

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
    def elemental_run_progress(self) -> pn.indicators.Progress:
        """Access the progress indicator for the active multipixel run."""
        return self._elemental_run_progress

    @property
    def elemental_results_view(self) -> NLLSResultsView:
        """Access the reactive Elemental NLLS reference-results view."""
        return self._elemental_results_view

    @property
    def elemental_multifit_controls(self) -> NLLSMultifitControls:
        """Access the sidebar controls of the dense Elemental NLLS runs."""
        return self._elemental_multifit_controls

    @property
    def elemental_results_section(self) -> SimpleDetails:
        """Access the collapsible 'Reference Fit' section of the Results tab."""
        return self._elemental_results_section

    @property
    def elemental_multifit_section(self) -> SimpleDetails:
        """Access the collapsible 'Elemental NLLS' section of the Results tab."""
        return self._elemental_multifit_section

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

        # Both sections start locked: the controller unlocks and opens them only once
        # background provenance AND geometry are valid, so an unusable source can never
        # expose Add Edge / Build Elemental Model.
        edge_details = self._elemental_edge_section = self._create_elemental_edge_section()
        model_details = self._elemental_model_section = self._create_elemental_model_section()

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
                self._elemental_run_progress,
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
        self._elemental_periodic_table_button = pn.widgets.ButtonIcon(
            icon=self._PERIODIC_TABLE_SVG,
            active_icon=self._PERIODIC_TABLE_ACTIVE_SVG,
            size="3em",
            margin=(21, 2, 0, 8),
        )
        self._edge_added_modal = EdgeAddedModal(
            self._custom_page,
            self._model,
            title=self._EDGE_ADDED_MODAL_ID,
            on_close=lambda: setattr(self._elemental_edges_added_button, "value", False),
        )
        if self._modal_manager is not None:
            self._modal_manager.register_modal(
                self._EDGE_ADDED_MODAL_ID,
                self._edge_added_modal,
            )
        self._elemental_periodic_table_button.on_click(self._open_periodic_table)
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
            start=constants.ELEMENTAL_CHEMICAL_SHIFT_MIN,
            end=constants.ELEMENTAL_CHEMICAL_SHIFT_MAX,
            step=constants.ELEMENTAL_CHEMICAL_SHIFT_STEP,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
        )

        content = pn.Column(
            pn.Row(
                self._elemental_input["element_atomic_number"],
                self._elemental_periodic_table_button,
                sizing_mode=self._STRETCH_WIDTH,
                styles=self._fluid_row_styles(**{"flex-wrap": "nowrap"}),
            ),
            self._elemental_input["subshells"],
            pn.Row(
                self._elemental_input["chemical_shift"],
                self._left_tooltip_icon(constants.CHEMICAL_SHIFT_TOOLTIP, width=30),
                sizing_mode=self._STRETCH_WIDTH,
                styles=self._fluid_row_styles(),
            ),
            self._elemental_onset_readout,
            pn.Row(
                self._elemental_add_edge_button,
                self._elemental_edges_added_button,
                sizing_mode=self._STRETCH_WIDTH,
                styles={
                    **self._fluid_row_styles(),
                    "align-items": "center",
                    "justify-content": "center",
                    "gap": "6px",
                },
            ),
            sizing_mode=self._STRETCH_WIDTH,
        )

        return SimpleDetails(
            title=constants.SECTION_ELEMENTAL_EDGE,
            content=content,
            expanded=True,
            locked=True,
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
        self._elemental_input["soften_edge"] = pn.widgets.Switch(
            value=constants.DEFAULT_ELEMENTAL_SOFTEN_EDGE,
            width=50,
            margin=0,
        )
        self._elemental_soften_label = pn.widgets.StaticText(
            value="Soften edge",
            height=24,
            margin=0,
            styles={
                "font-size": "1em",
                "white-space": "nowrap",
            },
        )
        self._elemental_soften_strength_label = pn.widgets.StaticText(
            value="Soften strength (eV)",
            height=24,
            margin=0,
            styles={
                "font-size": "1em",
                "white-space": "nowrap",
            },
        )
        self._elemental_input["soften_strength"] = pn.widgets.FloatInput(
            name="",
            value=constants.DEFAULT_ELEMENTAL_SOFTEN_STRENGTH,
            start=0.0,
            step=constants.ELEMENTAL_SOFTEN_STRENGTH_STEP,
            format="0.00",
            width=90,
            margin=0,
        )
        self._elemental_input["execution_mode"] = pn.widgets.Select(
            name="Execution mode",
            options={"Serial": False, "Parallel": True},
            value=False,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            stylesheets=["""
                .bk-input-group > label {
                    margin-bottom: 5px;
                }
            """],
        )
        cpu_count = max(1, int(os.cpu_count() or 1))
        self._elemental_input["workers"] = pn.widgets.IntInput(
            name="Parallel workers",
            value=max(1, cpu_count - 1),
            start=1,
            end=cpu_count,
            disabled=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
        )

        self._elemental_execution_controls = pn.Row(
            self._elemental_input["execution_mode"],
            self._elemental_input["workers"],
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=self._fluid_row_styles(
                **{
                    "box-sizing": "border-box",
                    "flex-wrap": "nowrap",
                    "gap": "12px",
                    "max-width": "100%",
                    "overflow": "hidden",
                }
            ),
            stylesheets=["""
                :host {
                    box-sizing: border-box !important;
                    max-width: 100% !important;
                    min-width: 0 !important;
                }
                :host > .bk-Row > * {
                    min-width: 0 !important;
                }
            """],
        )

        soften_edge_control = pn.Column(
            self._elemental_soften_label,
            self._elemental_input["soften_edge"],
            width=104,
            margin=0,
            styles={
                "align-items": "flex-start",
                "gap": "15px",
                "min-width": "0",
            },
        )
        soften_tooltip = self._left_tooltip_icon(
            constants.TOOLTIP_ELEMENTAL_SOFTEN,
            width=30,
            margin=0,
        )
        soften_strength_row = pn.Row(
            self._elemental_input["soften_strength"],
            soften_tooltip,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles=self._fluid_row_styles(
                **{
                    "align-items": "center",
                    "flex-wrap": "nowrap",
                    "gap": "8px",
                    "max-width": "100%",
                    "overflow": "hidden",
                }
            ),
        )
        soften_strength_control = pn.Column(
            self._elemental_soften_strength_label,
            soften_strength_row,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles={
                "align-items": "flex-start",
                "gap": "8px",
                "max-width": "100%",
                "min-width": "0",
                "overflow": "hidden",
            },
        )
        self._elemental_soften_controls = pn.Row(
            soften_edge_control,
            pn.Spacer(width=12, margin=0),
            soften_strength_control,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=self._fluid_row_styles(
                **{
                    "box-sizing": "border-box",
                    "flex-wrap": "nowrap",
                    "max-width": "100%",
                    "overflow": "hidden",
                    "width": "100%",
                }
            ),
            stylesheets=["""
                :host {
                    box-sizing: border-box !important;
                    max-width: 100% !important;
                    min-width: 0 !important;
                    width: 100% !important;
                }
            """],
        )

        content = pn.Column(
            self._elemental_input["model_composition"],
            self._elemental_input["elnes_shape"],
            self._elemental_input["flexibility"],
            self._elemental_soften_controls,
            self._elemental_execution_controls,
            self._elemental_build_model_button,
            sizing_mode=self._STRETCH_WIDTH,
        )

        return SimpleDetails(
            title=constants.SECTION_ELEMENTAL_MODEL,
            content=content,
            expanded=True,
            locked=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=dict(self._SECTION_CONTAINED),
        )

    def _create_results_tab(self) -> pn.Column:
        """Build the scrollable Results tab: one section per kind of NLLS result.

        Both blocks are controls only. Their plots are published to the main area, so
        the tab never mixes a menu with the figures it drives.
        """
        constants = self._model.constants

        self._elemental_results_section = SimpleDetails(
            title=constants.SECTION_RESULTS_REFERENCE,
            content=self._elemental_results_view,
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=dict(self._SECTION_CONTAINED),
        )
        self._elemental_multifit_section = SimpleDetails(
            title=constants.SECTION_RESULTS_ELEMENTAL,
            content=self._elemental_multifit_controls,
            expanded=True,
            sizing_mode=self._STRETCH_WIDTH,
            margin=(0, 10, 10, 10),
            styles=dict(self._SECTION_CONTAINED),
        )

        results_tab = pn.Column(
            self._elemental_results_section,
            self._elemental_multifit_section,
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
