"""Characterization tests protecting the pre-existing manual Fitting model.

The repository's ``whateels.pages`` package imports every page eagerly. These
tests register only the package paths needed by Fitting so the model can be
characterized without booting the complete Panel application.
"""

from __future__ import annotations

import importlib
import pathlib
import sys
import types
import unittest
from threading import Event
from types import SimpleNamespace

import numpy as np
import panel as pn
import xarray as xr
import holoviews as hv
from bokeh.document import Document
from bokeh.models import DataRange1d, LayoutDOM, Range1d, Tooltip
from whateels.components import DragGutter, ModalManager, SimpleDetails, SplitJs
from whateels.nlls.contracts import FitRange, ModelComposition, ReferenceFitSnapshot
from whateels.nlls.cross_sections import OOSCurveSnapshot
from whateels.nlls.defaults import OOS_FORMULA_VERSION, OOS_PROVIDER_VERSION, OOS_UNITS
from whateels.nlls.provenance import publish_power_law_subtracted_dataset
from whateels.nlls.results import FitStatus
from whateels.state.app_state import AppState


def _load_manual_fitting_symbols():
    import whateels

    root = pathlib.Path(__file__).resolve().parents[1]
    package_paths = {
        "whateels.pages": root / "whateels/pages",
        "whateels.pages.fitting": root / "whateels/pages/fitting",
        "whateels.pages.fitting.MVC": root / "whateels/pages/fitting/MVC",
    }
    for name, path in package_paths.items():
        if name in sys.modules:
            continue
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        package.__package__ = name
        sys.modules[name] = package

    model_module = importlib.import_module("whateels.pages.fitting.MVC.model")
    component_module = importlib.import_module(
        "whateels.pages.fitting.MVC.model.component_item"
    )
    return model_module.FittingModel, component_module.ComponentItem


FittingModel, ComponentItem = _load_manual_fitting_symbols()
FittingRightSidebarLayout = importlib.import_module(
    "whateels.pages.fitting.MVC.view.layouts.right_sidebar_layout"
).FittingRightSidebarLayout
SpectrumImageVisualizer = importlib.import_module(
    "whateels.pages.fitting.MVC.view.plots.spectrum_image_plot"
).SpectrumImageVisualizer
NLLSMultifitResultsPlot = importlib.import_module(
    "whateels.pages.fitting.MVC.view.plots.nlls_multifit_results_plot"
).NLLSMultifitResultsPlot
NLLSDerivedResultsPlot = importlib.import_module(
    "whateels.pages.fitting.MVC.view.plots.nlls_derived_results_plot"
).NLLSDerivedResultsPlot
NLLSMultifitControls = importlib.import_module(
    "whateels.pages.fitting.MVC.view.components.nlls_multifit_controls"
).NLLSMultifitControls
NLLSResultsView = importlib.import_module(
    "whateels.pages.fitting.MVC.view.components.nlls_results_view"
).NLLSResultsView
_layout_manager_module = importlib.import_module(
    "whateels.pages.fitting.MVC.controller.managers.layout_manager"
)
LayoutManager = _layout_manager_module.LayoutManager
StableAdditiveColumn = _layout_manager_module._StableAdditiveColumn


def _load_nlls_controller():
    path = pathlib.Path(__file__).resolve().parents[1] / (
        "whateels/pages/fitting/MVC/controller/nlls_controller.py"
    )
    spec = importlib.util.spec_from_file_location("nlls_controller_regression", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.NLLSController


NLLSController = _load_nlls_controller()


def _manual_dataset() -> xr.Dataset:
    eloss = np.linspace(0.0, 10.0, 101)
    peak = 4.0 * np.exp(-0.5 * ((eloss - 5.0) / 0.8) ** 2)
    cube = np.broadcast_to(peak, (2, 3, eloss.size)).copy()
    return xr.Dataset(
        {"ElectronCount": (("y", "x", "Eloss"), cube)},
        coords={"y": np.arange(2), "x": np.arange(3), "Eloss": eloss},
    )


def _reference_snapshot(area_id: str) -> ReferenceFitSnapshot:
    eloss = np.linspace(0.0, 3.0, 4)
    spectrum = eloss + 1.0
    best_fit = spectrum * 0.95
    return ReferenceFitSnapshot(
        area_id=area_id,
        success=True,
        message="Converged",
        method="leastsq",
        params=({"name": "amp", "value": 1.0, "stderr": 0.1, "vary": True},),
        redchi=0.02,
        reference_spectrum=spectrum,
        reference_strategy="clustering_mean",
        reference_pixel_count=3,
        reference_mask_fingerprint="fingerprint",
        best_fit=best_fit,
        residual=spectrum - best_fit,
        components={"h_k1_continuum_": best_fit},
        dataset_source_revision="plot-test",
        area_revision=1,
        model_composition=ModelComposition.CONTINUUM_ONLY,
        fit_range=FitRange(0.0, 3.0),
    )


def _dense_nlls_result() -> xr.Dataset:
    eloss = np.linspace(0.0, 4.0, 5)
    amplitudes = np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
    original = amplitudes[..., None] * (eloss + 1.0)[None, None, :]
    best_fit = original * 0.9
    residual = original - best_fit
    status = np.array(
        [
            [int(FitStatus.SUCCESS), int(FitStatus.SUCCESS), int(FitStatus.FIT_ERROR)],
            [int(FitStatus.NOT_SELECTED), int(FitStatus.SUCCESS), int(FitStatus.SUCCESS)],
        ],
        dtype=np.int8,
    )
    unsuccessful = status != int(FitStatus.SUCCESS)
    best_fit[unsuccessful] = np.nan
    residual[unsuccessful] = np.nan
    parameter = amplitudes.copy()
    parameter[unsuccessful] = np.nan
    stderr = np.full(amplitudes.shape, 0.05)
    stderr[unsuccessful] = np.nan
    dataset = xr.Dataset(
        {
            "OriginalData": (("y", "x", "Eloss"), original),
            "AreaLabel": (
                ("y", "x"),
                np.array([[0, 0, 0], [-1, 1, 1]], dtype=np.int32),
            ),
            "FitStatus": (("y", "x"), status),
            "ReducedChiSquare": (
                ("y", "x"),
                np.where(
                    status == int(FitStatus.SUCCESS), amplitudes * 0.01, np.nan
                ),
            ),
            "BestFit": (("y", "x", "Eloss"), best_fit),
            "Residuals": (("y", "x", "Eloss"), residual),
            "h_k1_continuum__component": (("y", "x", "Eloss"), best_fit),
            "h_k1_cont_A": (("y", "x"), parameter),
            "h_k1_cont_A__stderr": (("y", "x"), stderr),
        },
        coords={"y": np.arange(2), "x": np.arange(3), "Eloss": eloss},
        attrs={
            "selected_areas": '["cluster_0", "cluster_1"]',
            "method": "leastsq",
            "processed_pixels": 5,
            "selected_pixels": 5,
            "complete": 1,
            "cancelled": 0,
            "dataset_source_revision": "plot-test",
        },
    )
    dataset["AreaLabel"].attrs["area_ids_by_label"] = (
        '{"0": "cluster_0", "1": "cluster_1"}'
    )
    return dataset


def _derived_nlls_result() -> xr.Dataset:
    return xr.Dataset(
        {
            "Distances": (("y", "x"), np.array([[1.0, 2.0], [3.0, np.nan]])),
            "FitStatus": (
                ("y", "x"),
                np.array(
                    [
                        [int(FitStatus.SUCCESS), int(FitStatus.SUCCESS)],
                        [int(FitStatus.SUCCESS), int(FitStatus.FIT_ERROR)],
                    ],
                    dtype=np.int8,
                ),
            ),
            "AreaLabel": (
                ("y", "x"), np.array([[0, 0], [1, 1]], dtype=np.int32)
            ),
        },
        coords={"y": [0, 1], "x": [0, 1]},
        attrs={"analysis_type": "center_distance", "source_run_id": "parent"},
    )


class NLLSVisualPreviewTests(unittest.TestCase):
    def test_shifted_oos_preview_does_not_drop_to_zero_outside_support(self):
        snapshot = OOSCurveSnapshot(
            energy_eV=np.array([100.0, 110.0, 120.0], dtype=float),
            normalized_shape=np.array([0.0, 0.5, 0.0], dtype=float),
            physical_shape=np.array([0.0, 0.5, 0.0], dtype=float),
            normalization_factor=1.0,
            units=OOS_UNITS,
            formula_version=OOS_FORMULA_VERSION,
            provider_version=OOS_PROVIDER_VERSION,
            atomic_number=10,
            symbol="Ts",
            shells=("L2",),
            onsets_eV=(100.0,),
            table_checksums=("checksum",),
            broadening_sigma_eV=0.0,
            fit_range=FitRange(90.0, 130.0),
        )
        eloss = np.array([90.0, 105.0, 115.0, 130.0], dtype=float)

        preview = NLLSController._shifted_oos_preview(snapshot, eloss, 0.0)

        self.assertTrue(np.isnan(preview[0]))
        self.assertTrue(np.isfinite(preview[1]))
        self.assertTrue(np.isnan(preview[3]))
        self.assertFalse(np.any(preview == 0.0))

    def test_shifted_oos_preview_ignores_zero_values_without_hiding_real_onset(self):
        snapshot = OOSCurveSnapshot(
            energy_eV=np.array([95.0, 100.0, 105.0], dtype=float),
            normalized_shape=np.array([0.0, 0.5, 1.0], dtype=float),
            physical_shape=np.array([0.0, 0.5, 1.0], dtype=float),
            normalization_factor=1.0,
            units=OOS_UNITS,
            formula_version=OOS_FORMULA_VERSION,
            provider_version=OOS_PROVIDER_VERSION,
            atomic_number=10,
            symbol="Ts",
            shells=("L2",),
            onsets_eV=(100.0,),
            table_checksums=("checksum",),
            broadening_sigma_eV=0.0,
            fit_range=FitRange(90.0, 130.0),
        )
        eloss = np.array([95.0, 99.0, 100.0, 101.0], dtype=float)

        preview = NLLSController._shifted_oos_preview(snapshot, eloss, 0.0)

        self.assertTrue(np.isnan(preview[0]))
        self.assertTrue(np.isnan(preview[1]))
        self.assertTrue(np.isfinite(preview[2]))
        self.assertTrue(np.isfinite(preview[3]))
        self.assertFalse(np.any(preview == 0.0))


def _current_map(view):
    current = getattr(view, "current_map_plot", None)
    return current if current is not None else view.map_pane.object


def _current_spectrum(view):
    current = getattr(view, "current_spectrum_plot", None)
    return current if current is not None else view.spectrum_pane.object


class ManualFittingRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.model = FittingModel()
        self.state = self.model.app_state
        self.dataset = _manual_dataset()
        self.state.plot_dataset = self.dataset
        self.state.spectra = np.asarray(self.dataset["ElectronCount"].mean(("y", "x")))

    def tearDown(self) -> None:
        self.state.spectra = None
        self.state.fitting_results = None
        self.state.plot_dataset = None

    def _add_gaussian(self):
        item = ComponentItem(5.0, "GaussianModel", (3.0, 7.0), "Medium")
        self.model.add_component(item, "Medium")
        return item

    def test_add_fit_and_remove_component_contract(self):
        item = self._add_gaussian()
        self.assertEqual(len(self.model.dictionary["components"]), 1)
        self.assertTrue(self.model.ref_results.success)
        self.assertEqual(self.model.ref_results.best_fit.shape, (101,))

        self.assertTrue(self.model.remove_component(item))
        self.assertEqual(self.model.dictionary["components"], [])
        self.assertIsNone(self.model.ref_results)
        self.assertIsNone(self.state.fitting_results)

    def test_energy_map_keeps_existing_sum_definition(self):
        self._add_gaussian()
        self.state.fitting_results = np.asarray(self.model.ref_results.best_fit)
        actual = self.model.get_energy_map()

        eloss = np.asarray(self.dataset.coords["Eloss"])
        mask = (eloss >= 3.0) & (eloss <= 7.0)
        expected = np.sum(
            np.asarray(self.dataset["ElectronCount"])[..., mask]
            + self.state.fitting_results[mask][None, None, :],
            axis=-1,
        )
        np.testing.assert_allclose(actual, expected)

    def test_source_reset_clears_manual_derived_state(self):
        self._add_gaussian()
        self.state.fitting_results = np.asarray(self.model.ref_results.best_fit)
        self.model.reset_for_data_source_change()
        self.assertEqual(self.model.dictionary["components"], [])
        self.assertIsNone(self.model.ref_results)
        self.assertIsNone(self.state.fitting_results)

    def test_clear_nlls_state_does_not_reuse_manual_fields(self):
        manual_result = np.array([1.0, 2.0])
        self.state.fitting_results = manual_result
        self.state.nlls_workspace = object()
        self.state.nlls_results = object()
        previous_revision = self.state.nlls_revision
        self.state.clear_nlls_state()
        self.assertIs(self.state.fitting_results, manual_result)
        self.assertIsNone(self.state.nlls_workspace)
        self.assertIsNone(self.state.nlls_results)
        self.assertEqual(self.state.nlls_run_state, "idle")
        self.assertEqual(self.state.nlls_revision, previous_revision + 1)

    def test_fitting_tooltips_open_left_and_clustering_file_input_is_removed(self):
        layout = FittingRightSidebarLayout(self.model)
        tooltips = layout.select(pn.widgets.TooltipIcon)
        # Subshells intentionally has no help icon; the remaining help popups
        # must still open toward the inside of the sidebar.
        self.assertGreaterEqual(len(tooltips), 3)
        self.assertTrue(
            all(
                isinstance(icon.value, Tooltip) and icon.value.position == "left"
                for icon in tooltips
            )
        )
        self.assertFalse(hasattr(layout, "elemental_load_clustering_json_input"))
        self.assertEqual(layout.select(pn.widgets.FileInput), [])

    def test_oos_method_and_status_information_is_fully_removed(self):
        layout = FittingRightSidebarLayout(self.model)
        details = layout.select(SimpleDetails)
        detail_titles = {detail._title for detail in details}
        self.assertNotIn("OOS Status", detail_titles)
        self.assertNotIn("Areas", detail_titles)
        self.assertNotIn("Run Setup", detail_titles)
        static_names = {
            str(widget.name) for widget in layout.select(pn.widgets.StaticText)
        }
        self.assertNotIn("OOS method / version", static_names)
        markdown = "\n".join(
            str(pane.object) for pane in layout.select(pn.pane.Markdown)
        )
        self.assertNotIn("**OOS status:**", markdown)
        self.assertNotIn("Load Clustering JSON", markdown)
        button_names = {button.name for button in layout.select(pn.widgets.Button)}
        self.assertNotIn("Reset Area", button_names)
        self.assertNotIn("Build Elemental Model", button_names)
        self.assertNotIn("Fit Current Reference", button_names)
        self.assertNotIn("Fit All References", button_names)
        self.assertIn("Fit", button_names)
        fit_rows = [
            row
            for row in layout.select(pn.Row)
            if layout.elemental_fit_button in row.objects
        ]
        self.assertTrue(fit_rows)
        self.assertIn(
            layout.elemental_fit_area_settings_button,
            fit_rows[0].objects,
        )
        self.assertIn(
            layout.elemental_use_current_clustering_button,
            layout._elemental_fit_areas_modal.objects,
        )

    def test_elemental_sections_start_locked_below_both_status_alerts(self):
        layout = FittingRightSidebarLayout(self.model)
        edge = layout.elemental_edge_section
        model = layout.elemental_model_section
        continuum = layout.elemental_continuum_section
        elnes = layout.elemental_elnes_section
        background = layout.elemental_background_status
        geometry = layout.elemental_geometry_status

        # No controller has validated a source yet, so nothing may be opened.
        self.assertTrue(background.visible)
        self.assertTrue(geometry.visible)
        for section in (edge, model, continuum, elnes):
            self.assertTrue(section.locked)
            self.assertFalse(section.expanded)
            self.assertTrue(section._button_header.disabled)
            section.toggle()
            self.assertFalse(section.expanded)

        container = next(
            column
            for column in layout.fitting_tabs[1].select(pn.Column)
            if "elemental-input-container" in column.css_classes
        )
        self.assertEqual(
            container.objects,
            [background, geometry, edge, model, continuum, elnes],
        )

    def test_results_tab_uses_reactive_elemental_results_view(self):
        layout = FittingRightSidebarLayout(self.model)
        results = layout.elemental_results_view
        self.assertTrue(results.area_select.disabled)
        self.assertEqual(results.area_select.options, {})
        self.assertFalse(results.plot_pane.visible)
        self.assertNotIn(
            "Elemental NLLS results will be shown here once available.",
            "\n".join(str(pane.object) for pane in layout.select(pn.pane.Markdown)),
        )

    def test_results_tab_wraps_both_controls_in_their_own_section(self):
        layout = FittingRightSidebarLayout(self.model)
        reference = layout.elemental_results_section
        elemental = layout.elemental_multifit_section
        results_tab = layout.fitting_tabs[2]

        self.assertEqual(results_tab.objects, [reference, elemental])
        for section in (reference, elemental):
            self.assertIsInstance(section, SimpleDetails)
            self.assertTrue(section.expanded)
            self.assertFalse(section.locked)
        self.assertIn(layout.elemental_results_view, reference.select(NLLSResultsView))
        self.assertIn(
            layout.elemental_multifit_controls,
            elemental.select(NLLSMultifitControls),
        )
        # The multifit controls start empty: no run has been published yet.
        self.assertEqual(layout.elemental_multifit_controls.runs, ())
        self.assertFalse(layout.elemental_multifit_controls.run_select.visible)

    def test_reference_summary_drops_the_repeated_area_title(self):
        view = NLLSResultsView()
        snapshot = _reference_snapshot("cluster_0")
        view.render({"cluster_0": snapshot}, {"cluster_0": "Cluster 0"}, np.arange(4.0))

        summary = view.summary_pane.object
        self.assertIn("Reduced χ²", summary)
        self.assertIn("Cluster mean", summary)
        # The selector above already names the area, so neither the label nor the
        # magenta title band may come back into the card.
        self.assertNotIn("Cluster 0", summary)
        self.assertNotIn("background:#ca4bc8", summary.replace(" ", ""))

    def test_elemental_actions_use_a_full_height_scroll_layout(self):
        layout = FittingRightSidebarLayout(self.model)
        self.assertEqual(layout.sizing_mode, "stretch_both")
        self.assertEqual(layout.fitting_tabs.sizing_mode, "stretch_both")
        elemental_tab = layout.fitting_tabs[1]
        self.assertEqual(elemental_tab.margin, 0)
        self.assertEqual(elemental_tab.styles.get("height"), "100%")
        self.assertEqual(elemental_tab.styles.get("min-height"), "0")
        columns = elemental_tab.select(pn.Column)
        input_container = next(
            column
            for column in columns
            if "elemental-input-container" in column.css_classes
        )
        action_container = next(
            column for column in columns if "elemental-actions" in column.css_classes
        )
        self.assertEqual(input_container.styles.get("flex"), "1 1 0")
        self.assertEqual(input_container.styles.get("overflow-y"), "auto")
        self.assertEqual(action_container.styles.get("flex-shrink"), "0")
        self.assertEqual(action_container.styles.get("padding"), "10px")
        self.assertIn(layout.elemental_run_progress, action_container.objects)
        self.assertFalse(layout.elemental_run_progress.visible)

    def test_elemental_sections_do_not_clip_subshell_dropdown(self):
        layout = FittingRightSidebarLayout(self.model)

        # The tab-level container remains the vertical scrolling boundary, but
        # each card must let floating widget menus overlap the following card.
        for section in (
            layout.elemental_edge_section,
            layout.elemental_model_section,
        ):
            self.assertEqual(section.styles.get("overflow"), "visible")
            self.assertNotIn("overflow-x", section.styles)
            self.assertNotIn("overflow-y", section.styles)

        elemental_tab = layout.fitting_tabs[1]
        input_container = next(
            column
            for column in elemental_tab.select(pn.Column)
            if "elemental-input-container" in column.css_classes
        )
        self.assertEqual(input_container.styles.get("overflow-y"), "auto")

    def test_subshell_onsets_are_styled_as_right_aligned_secondary_text(self):
        stylesheet = NLLSController._subshell_onset_stylesheet(
            {"K1": 4940.7229, "L3": 465.18447}
        )

        self.assertIn('data-value="K1"', stylesheet)
        self.assertIn('data-value="L3"', stylesheet)
        self.assertIn('--subshell-onset: "4941 eV"', stylesheet)
        self.assertIn('--subshell-onset: "465 eV"', stylesheet)
        self.assertIn("grid-template-columns: minmax(0, 1fr) auto", stylesheet)
        self.assertIn("text-align: right", stylesheet)
        self.assertIn(NLLSController._SUBSHELL_ONSET_COLOR, stylesheet)
        self.assertIn(NLLSController._SUBSHELL_ONSET_HIGHLIGHT_COLOR, stylesheet)

    def test_subshell_control_has_no_help_icon(self):
        layout = FittingRightSidebarLayout(self.model)
        subshell = layout.elemental_input["subshells"]

        parent_rows = [row for row in layout.select(pn.Row) if subshell in row.objects]
        self.assertEqual(parent_rows, [])

    def test_chemical_shift_uses_twenty_ev_limits_and_two_decimal_display(self):
        layout = FittingRightSidebarLayout(self.model)
        chemical_shift = layout.elemental_input["chemical_shift"]

        self.assertEqual(chemical_shift.start, -20.0)
        self.assertEqual(chemical_shift.end, 20.0)
        self.assertEqual(chemical_shift.step, 0.01)
        self.assertEqual(chemical_shift.format, "0.00")

    def test_element_atomic_number_has_periodic_table_modal_button(self):
        class PageStub:
            def __init__(self):
                self.modal = pn.Column()
                self.opened = False
                self.closed = False

            def open_modal(self):
                self.opened = True

            def close_modal(self):
                self.closed = True

        page = PageStub()
        modal_manager = ModalManager(page)
        layout = FittingRightSidebarLayout(
            self.model,
            custom_page=page,
            modal_manager=modal_manager,
        )
        atomic_number = layout.elemental_input["element_atomic_number"]
        button = layout.elemental_periodic_table_button
        parent_rows = [row for row in layout.select(pn.Row) if atomic_number in row.objects]

        self.assertEqual(len(parent_rows), 1)
        self.assertIn(button, parent_rows[0].objects)
        self.assertIn(">E</text>", button.icon)
        self.assertIn(layout.periodic_table_modal, modal_manager.modals)

        layout._open_periodic_table()
        self.assertTrue(page.opened)
        self.assertTrue(layout.periodic_table_modal.visible)
        self.assertIn(layout.periodic_table_modal, page.modal.objects)

        layout.periodic_table_modal._close()
        self.assertTrue(page.closed)
        self.assertFalse(layout.periodic_table_modal.visible)

    def test_soften_edge_uses_a_single_line_switch_layout(self):
        layout = FittingRightSidebarLayout(self.model)
        soften_switch = layout.elemental_input["soften_edge"]
        soften_strength = layout.elemental_input["soften_strength"]

        self.assertIsInstance(soften_switch, pn.widgets.Switch)
        self.assertNotIsInstance(soften_switch, pn.widgets.Checkbox)
        controls = layout._elemental_soften_controls
        self.assertIsInstance(controls, pn.Row)
        self.assertEqual(controls.styles.get("max-width"), "100%")
        self.assertEqual(controls.styles.get("overflow"), "hidden")
        self.assertEqual(len(controls.objects), 3)
        self.assertIsInstance(controls.objects[1], pn.Spacer)
        self.assertEqual(controls.objects[1].width, 12)
        strength_control = controls.objects[2]
        self.assertIsInstance(strength_control, pn.Column)
        self.assertEqual(soften_strength.width, 90)
        self.assertEqual(soften_strength.format, "0.00")
        self.assertEqual(soften_strength.step, 0.01)
        strength_stylesheet = "\n".join(str(item) for item in soften_strength.stylesheets)
        self.assertNotIn("translateX", strength_stylesheet)
        self.assertEqual(soften_strength.name, "")
        self.assertEqual(layout._elemental_soften_label.value, "Soften edge")
        self.assertEqual(
            layout._elemental_soften_strength_label.value,
            "Soften strength (eV)",
        )
        self.assertEqual(
            strength_control.objects[0],
            layout._elemental_soften_strength_label,
        )
        strength_rows = [
            row for row in strength_control.select(pn.Row)
            if soften_strength in row.objects
        ]
        self.assertEqual(len(strength_rows), 1)
        self.assertIs(strength_control.objects[1], strength_rows[0])
        self.assertIs(strength_rows[0].objects[0], soften_strength)
        self.assertIsInstance(strength_rows[0].objects[1], pn.widgets.TooltipIcon)
        self.assertEqual(strength_rows[0].objects[1].width, 30)
        switch_columns = [
            column for column in controls.select(pn.Column)
            if soften_switch in column.objects
        ]
        self.assertEqual(len(switch_columns), 1)
        self.assertEqual(
            switch_columns[0].objects,
            [layout._elemental_soften_label, soften_switch],
        )
        self.assertEqual(switch_columns[0].styles.get("gap"), "8px")
        self.assertEqual(strength_control.styles.get("gap"), "8px")
        self.assertIs(controls.objects[0], switch_columns[0])

    def test_execution_mode_and_parallel_workers_share_one_row(self):
        layout = FittingRightSidebarLayout(self.model)
        execution_mode = layout.elemental_input["execution_mode"]
        workers = layout.elemental_input["workers"]
        controls = layout._elemental_execution_controls

        self.assertIsInstance(controls, pn.Row)
        self.assertEqual(controls.objects, [execution_mode, workers])
        self.assertEqual(controls.styles.get("flex-wrap"), "nowrap")
        self.assertEqual(controls.styles.get("gap"), "12px")
        self.assertNotIn("width", controls.styles)
        self.assertEqual(execution_mode.margin, 0)
        self.assertEqual(workers.margin, 0)
        execution_stylesheet = "\n".join(
            str(item) for item in execution_mode.stylesheets
        )
        self.assertIn("margin-bottom: 5px", execution_stylesheet)

    def test_edge_definition_preview_scales_oos_without_touching_manual_state(self):
        visualizer = SpectrumImageVisualizer(self.model, self.dataset)
        energy = np.asarray(self.dataset.coords["Eloss"], dtype=float)
        normalized_oos = np.exp(-0.5 * ((energy - 4.0) / 0.65) ** 2)
        reference = 250.0 * normalized_oos
        original_oos = normalized_oos.copy()
        previous_plot = visualizer._paneB_pipe.data

        try:
            visualizer.show_nlls_edge_preview(
                energy,
                reference,
                (("H K1 OOS", energy, normalized_oos),),
                spectrum_label="ROI mean",
            )

            self.assertTrue(visualizer.nlls_edge_preview_active)
            preview = visualizer._paneB_pipe.data
            self.assertIsInstance(preview, hv.Overlay)
            preview_curves = [
                element for element in preview if isinstance(element, hv.Curve)
            ]
            self.assertEqual(
                {curve.label for curve in preview_curves},
                {"ROI mean", "H K1 OOS"},
            )
            oos_curve = next(
                curve for curve in preview_curves if curve.label == "H K1 OOS"
            )
            self.assertAlmostEqual(
                float(np.max(oos_curve.dimension_values("y"))),
                250.0,
                places=5,
            )
            np.testing.assert_allclose(normalized_oos, original_oos)
            self.assertIsNone(self.state.fitting_results)

            visualizer._current_x_range = (3.0, 5.0)
            visualizer._current_y_range = (0.0, 300.0)
            shifted_oos = np.interp(
                energy + 0.1,
                energy,
                normalized_oos,
                left=0.0,
                right=0.0,
            )
            visualizer.show_nlls_edge_preview(
                energy,
                reference,
                (("H K1 OOS (shift +0.1 eV)", energy, shifted_oos),),
                spectrum_label="ROI mean",
            )
            self.assertEqual(visualizer._current_x_range, (3.0, 5.0))
            self.assertEqual(visualizer._current_y_range, (0.0, 300.0))

            visualizer.clear_nlls_edge_preview()
            self.assertFalse(visualizer.nlls_edge_preview_active)
            self.assertIsNone(visualizer._nlls_edge_preview_plot)
            self.assertIs(visualizer._paneB_pipe.data, previous_plot)
        finally:
            visualizer.cleanup()

    def test_elemental_preview_keeps_amplitude_visible_with_a_unit_scale_basis(self):
        visualizer = SpectrumImageVisualizer(self.model, self.dataset)
        energy = np.asarray(self.dataset.coords["Eloss"], dtype=float)
        unit_gaussian = np.exp(-0.5 * ((energy - 4.0) / 0.65) ** 2)
        reference = 100.0 * unit_gaussian

        try:
            visualizer.show_nlls_edge_preview(
                energy,
                reference,
                (("H K1 Gaussian", energy, 2.0 * unit_gaussian),),
                spectrum_label="ROI mean",
                scale_bases=(unit_gaussian,),
            )
            preview = visualizer._paneB_pipe.data
            gaussian = next(
                curve
                for curve in preview
                if isinstance(curve, hv.Curve) and curve.label == "H K1 Gaussian"
            )
            self.assertAlmostEqual(
                float(np.max(gaussian.dimension_values("y"))),
                200.0,
                places=5,
            )
        finally:
            visualizer.cleanup()

    def test_edge_definition_preview_restores_an_existing_nlls_result(self):
        visualizer = SpectrumImageVisualizer(self.model, self.dataset)
        energy = np.asarray(self.dataset.coords["Eloss"], dtype=float)
        result_plot = hv.Overlay(
            [hv.Curve((energy, np.ones_like(energy)), label="NLLS result")]
        )

        try:
            visualizer.show_nlls_reference_result(result_plot)
            previous_plot = visualizer._paneB_pipe.data
            visualizer.show_nlls_edge_preview(
                energy,
                np.ones_like(energy),
                (("H K1 OOS", energy, np.ones_like(energy)),),
            )

            self.assertFalse(visualizer.nlls_result_active)
            visualizer.clear_nlls_edge_preview()

            self.assertTrue(visualizer.nlls_result_active)
            self.assertIs(visualizer._paneB_pipe.data, previous_plot)
        finally:
            visualizer.cleanup()

    def test_main_panels_switch_from_image_and_roi_to_clustering_and_result(self):
        visualizer = SpectrumImageVisualizer(self.model, self.dataset)

        def spatial_figure():
            # Inspect the model mounted by ``plots_layout``.  Calling
            # ``paneA.get_root()`` here would create a fresh document after
            # every object swap and could not catch a transition-only loss of
            # geometry hooks.
            return next(iter(visualizer.paneA._models.values()))[0]

        def assert_square_frame(figure, *, has_colorbar):
            """paneA splits the geometry into two jobs that must not overlap.

            The CSS container fills the height and derives the width from the
            image ratio; the figure then fills that container and only has to
            keep the DATA pixels square inside whatever the title and the colour
            bar leave over. Moving the outer shape onto the figure instead - via
            a scale_* mode, or via square_pixel_plot_hook - is what stretched the
            map, overflowed the split or made paneA vanish, depending on which
            one was tried.
            """
            # The figure fills the box CSS gave it. Under 'stretch_both' Bokeh
            # ignores aspect_ratio, which is deliberate: the shape comes from
            # the container, and this is the mode that re-solves when the pane
            # changes size.
            self.assertEqual(figure.sizing_mode, "stretch_both")
            # Re-checked in every paneA state: the energy map and the cluster
            # map may carry a different spatial shape than the source cube, and
            # a stale ratio would size them to the wrong box.
            self.assertAlmostEqual(
                visualizer._plots_gutter.pane_ratio,
                visualizer._nx / visualizer._ny,
            )
            # match_aspect is what keeps the data pixels square inside the box.
            self.assertTrue(figure.match_aspect)
            self.assertEqual(figure.aspect_scale, 1)
            # 'aspect' pins the ranges to the real data bounds, so they are
            # Range1d rather than the auto-ranging DataRange1d.
            self.assertIsInstance(figure.x_range, Range1d)
            self.assertIsInstance(figure.y_range, Range1d)
            self.assertLess(figure.x_range.start, figure.x_range.end)
            # invert_yaxis=True: rows run top to bottom.
            self.assertGreater(figure.y_range.start, figure.y_range.end)
            colorbars = [
                panel for panel in figure.right
                if type(panel).__name__ == "ColorBar"
            ]
            self.assertEqual(bool(colorbars), has_colorbar)
            self.assertTrue(all(colorbar.visible for colorbar in colorbars))

        try:
            plots_layout = visualizer.create_plots()
            self.assertIsNotNone(plots_layout.get_root())
            self.assertIsInstance(plots_layout, pn.Row)
            self.assertEqual(len(plots_layout.objects), 3)
            left_column, gutter, right_column = plots_layout.objects
            self.assertIsInstance(left_column, pn.Column)
            self.assertIsInstance(gutter, DragGutter)
            self.assertIsInstance(right_column, pn.Column)
            self.assertEqual(gutter.width, 10)
            self.assertEqual(gutter.sizing_mode, "stretch_height")
            self.assertEqual(left_column.sizing_mode, "stretch_both")
            self.assertEqual(right_column.sizing_mode, "stretch_both")
            # Centring belongs on paneA, never on the column that holds it.
            # Panel maps align to align-self, which on a Row is the vertical
            # axis: it drops the column to content height, and a height-driven
            # paneA then has nothing to measure and collapses to zero.
            self.assertNotEqual(left_column.align, "center")
            # The gutter locates the row and its panes by marker class; without
            # them dragging silently does nothing.
            self.assertIn(DragGutter.ROW_CSS_CLASS, plots_layout.css_classes)
            self.assertIn(DragGutter.PANE_CSS_CLASS, left_column.css_classes)
            self.assertIn(DragGutter.PANE_CSS_CLASS, right_column.css_classes)
            for pane in (left_column, right_column):
                self.assertEqual(pane.styles.get("min-width"), "0")
            # Guard for the frames between two local Bokeh solves: a fixed paneA
            # would otherwise paint past the gutter and over the right pane.
            self.assertEqual(left_column.styles.get("overflow"), "hidden")
            self.assertFalse(plots_layout.select(SplitJs))
            # paneA is left exactly as the base builds it for Home, Clustering
            # and Quantification: auto margins, so once the gutter has sized
            # paneA the leftover space becomes an even margin on both sides.
            # The gutter holds paneA by plain reference and runs SplitJs' fit on
            # its Bokeh model locally, persisting only the final box in Python.
            self.assertIs(visualizer._plots_gutter._ratio_pane, visualizer.paneA)
            self.assertIn(
                DragGutter.RATIO_PANE_CSS_CLASS,
                spatial_figure().css_classes,
            )
            self.assertEqual(visualizer.paneA.styles.get("margin"), "auto")
            self.assertNotEqual(visualizer.paneA.styles.get("overflow"), "hidden")
            # Nothing may pin paneA before the browser has reported a box: the
            # first measurement is what establishes the fitted size.
            self.assertIsNone(visualizer.paneA.width)
            self.assertIsNone(visualizer.paneA.height)
            assert_square_frame(spatial_figure(), has_colorbar=False)
            labels = np.array([[0, 0, 1], [0, 1, 1]], dtype=int)
            energy = np.asarray(self.dataset.coords["Eloss"], dtype=float)
            cube = np.asarray(self.dataset["ElectronCount"], dtype=float)
            spectra = (
                (0, "Cluster 0", cube[labels == 0].mean(axis=0)),
                (1, "Cluster 1", cube[labels == 1].mean(axis=0)),
            )
            visualizer.show_nlls_clustering(labels, energy, spectra)
            clustering_renderer = visualizer.paneB.object
            self.assertTrue(visualizer.nlls_clustering_active)
            self.assertIs(visualizer.paneA.object, visualizer._nlls_clustering_label_plot)
            self.assertIsInstance(visualizer.paneA.object, hv.Overlay)
            clustering_images = tuple(
                element
                for element in visualizer.paneA.object
                if isinstance(element, hv.Image)
            )
            self.assertEqual(len(clustering_images), 1)
            self.assertFalse(
                any(
                    isinstance(element, hv.Segments)
                    for element in visualizer.paneA.object
                )
            )
            np.testing.assert_array_equal(
                clustering_images[0].dimension_values("Cluster", flat=False),
                labels,
            )
            self.assertEqual(
                tuple(float(value) for value in clustering_images[0].bounds.lbrt()),
                (-0.5, -0.5, 2.5, 1.5),
            )
            self.assertIs(
                visualizer._paneB_pipe.data,
                visualizer._nlls_clustering_spectra_plot,
            )
            cluster_figure = spatial_figure()
            self.assertTrue(cluster_figure.right)
            self.assertTrue(cluster_figure.right[0].visible)
            assert_square_frame(cluster_figure, has_colorbar=True)

            fit_plot = hv.Overlay(
                [hv.Curve((energy, spectra[0][2]), label="Reference")]
            ).opts(
                hv.opts.Overlay(
                    xlabel="Energy loss (eV)",
                    ylabel="Electron count",
                    responsive=True,
                    shared_axes=False,
                )
            )
            visualizer.show_nlls_reference_result(fit_plot)
            reference_renderer = visualizer.paneB.object
            self.assertTrue(visualizer.nlls_result_active)
            self.assertIs(visualizer._paneB_pipe.data, fit_plot)
            self.assertIsNot(reference_renderer, clustering_renderer)
            reference_figure = next(
                model
                for model in visualizer.paneB.get_root().select({"type": LayoutDOM})
                if type(model).__name__ == "figure"
            )
            energy_axis = reference_figure.xaxis[0]
            self.assertIn(energy_axis, reference_figure.below)
            self.assertTrue(energy_axis.visible)
            self.assertEqual(energy_axis.axis_label, "Energy loss (eV)")

            # Data-only changes retain the figure; changing the visible curve
            # composition (as the Reference/Best fit/Components/Residual buttons
            # do) creates the renderer tree required by the new overlay.
            updated_fit_plot = hv.Overlay(
                [hv.Curve((energy, spectra[1][2]), label="Reference")]
            )
            visualizer.show_nlls_reference_result(updated_fit_plot)
            self.assertIs(visualizer.paneB.object, reference_renderer)
            fit_with_best = hv.Overlay(
                [
                    hv.Curve((energy, spectra[0][2]), label="Reference"),
                    hv.Curve((energy, spectra[1][2]), label="Best fit"),
                ]
            )
            visualizer.show_nlls_reference_result(fit_with_best)
            self.assertIsNot(visualizer.paneB.object, reference_renderer)
            self.assertIs(visualizer._paneB_pipe.data, fit_with_best)

            visualizer.clear_nlls_reference_result()
            self.assertFalse(visualizer.nlls_result_active)
            self.assertIs(
                visualizer._paneB_pipe.data,
                visualizer._nlls_clustering_spectra_plot,
            )
            visualizer.plot_energy_map(np.arange(labels.size).reshape(labels.shape))
            assert_square_frame(spatial_figure(), has_colorbar=True)
        finally:
            visualizer.cleanup()


class NLLSMultifitResultsPlotTests(unittest.TestCase):
    def test_result_view_switches_maps_and_pixel_spectra(self):
        view = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=3)
        try:
            self.assertEqual(view.selected_pixel, (0, 0))
            self.assertIn("Reduced χ²", view.map_select.options)
            self.assertIn("Fit status", view.map_select.options)
            self.assertIn("Parameter — h k1 cont A", view.map_select.options)
            self.assertIn("Std. error — h k1 cont A", view.map_select.options)
            self.assertIsInstance(_current_map(view), hv.Overlay)
            self.assertIsNotNone(
                _current_spectrum(view).get(("Curve", "Best_fit"))
            )
            rendered_root = view.get_root()
            map_model = view.map_pane.object
            spectrum_model = view.spectrum_pane.object
            map_bokeh_models = tuple(
                id(value[0]) for value in view.map_pane._models.values()
            )
            spectrum_bokeh_models = tuple(
                id(value[0]) for value in view.spectrum_pane._models.values()
            )

            map_figure = next(
                model
                for model in rendered_root.select({"type": LayoutDOM})
                if type(model).__name__ == "figure"
                and str(model.title.text).startswith("Run 3")
                and "Pixel" not in str(model.title.text)
            )
            self.assertIn("tap", map_figure._event_callbacks)
            self.assertIs(view._tap_stream.source, view.map_pane.object)

            view.map_select.value = "FitStatus"
            view._tap_stream.event(x=2, y=1)
            self.assertEqual(view.selected_pixel, (1, 2))
            self.assertIn("y=1, x=2", view.pixel_summary.object)
            # Aspect-preserving ranges can create blank padding around the
            # image. A tap there must not be clipped onto an edge pixel.
            view._tap_stream.event(x=-1, y=1)
            self.assertEqual(view.selected_pixel, (1, 2))
            view._tap_stream.event(x=2, y=2)
            self.assertEqual(view.selected_pixel, (1, 2))
            self.assertIs(view.map_pane.object, map_model)
            self.assertIs(view.spectrum_pane.object, spectrum_model)
            self.assertEqual(
                tuple(id(value[0]) for value in view.map_pane._models.values()),
                map_bokeh_models,
            )
            self.assertEqual(
                tuple(id(value[0]) for value in view.spectrum_pane._models.values()),
                spectrum_bokeh_models,
            )
            view.layer_selector.value = ["Residual"]
            self.assertIsNotNone(
                _current_spectrum(view).get(("Curve", "Residual"))
            )
            self.assertIsNotNone(rendered_root)
        finally:
            view.cleanup()

    def test_area_overlay_draws_fill_and_explicit_cluster_boundaries(self):
        view = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        try:
            self.assertTrue(view.area_fill_button.value)
            self.assertTrue(view.area_boundaries_button.value)
            self.assertEqual(view.area_fill_button.name, "Fill")
            self.assertEqual(view.area_boundaries_button.name, "Boundaries")
            self.assertIsNot(view.area_fill_button, view.area_boundaries_button)
            self.assertEqual(
                view.area_overlay_controls.objects,
                [view.area_fill_button, view.area_boundaries_button],
            )
            expected_segments = len(view._area_boundary_segments())
            self.assertGreater(expected_segments, 4)
            self.assertGreaterEqual(
                sum(isinstance(element, hv.Image) for element in _current_map(view)),
                2,
            )
            boundary_layers = tuple(
                element
                for element in _current_map(view)
                if isinstance(element, hv.Segments)
            )
            self.assertEqual(len(boundary_layers), 2)
            self.assertTrue(
                all(len(layer.dimension_values("x0")) == expected_segments
                    for layer in boundary_layers)
            )
            self.assertIn("cluster_0", view._pixel_summary_html(0, 0))

            view.area_boundaries_button.value = False
            self.assertEqual(
                sum(
                    isinstance(element, hv.Segments)
                    for element in _current_map(view)
                ),
                0,
            )

            view.area_fill_button.value = False
            view.area_boundaries_button.value = True
            self.assertEqual(
                sum(isinstance(element, hv.Image) for element in _current_map(view)),
                1,
            )
            self.assertEqual(
                sum(
                    isinstance(element, hv.Segments)
                    for element in _current_map(view)
                ),
                2,
            )

            rendered = hv.render(_current_map(view), backend="bokeh")
            rendered_segments = [
                renderer
                for renderer in rendered.renderers
                if type(getattr(renderer, "glyph", None)).__name__ == "Segment"
            ]
            self.assertEqual(len(rendered_segments), 2)
            self.assertTrue(
                all(
                    len(renderer.data_source.data["x0"]) == expected_segments
                    for renderer in rendered_segments
                )
            )
        finally:
            view.cleanup()

    def test_status_redchi_and_relative_error_share_one_pixel_mask(self):
        view = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        try:
            view.status_filter.value = [int(FitStatus.FIT_ERROR)]
            self.assertEqual(int(np.count_nonzero(view.visible_pixel_mask)), 1)
            self.assertEqual(view.selected_pixel, (0, 2))
            view._on_pixel_tapped(x=0, y=0)
            self.assertEqual(view.selected_pixel, (0, 2))

            view.status_filter.value = [int(FitStatus.SUCCESS)]
            view.max_redchi_input.value = 0.015
            self.assertEqual(int(np.count_nonzero(view.visible_pixel_mask)), 1)
            self.assertEqual(view.selected_pixel, (0, 0))

            view.max_redchi_input.value = None
            view.map_select.value = "h_k1_cont_A"
            self.assertFalse(view.max_relative_error_input.disabled)
            view.max_relative_error_input.value = 0.02
            self.assertEqual(int(np.count_nonzero(view.visible_pixel_mask)), 2)
            self.assertEqual(view.selected_pixel, (1, 1))
            self.assertIn("Relative error", view.pixel_summary.object)

            view.status_filter.value = []
            self.assertFalse(np.any(view.visible_pixel_mask))
            self.assertIn("No pixels match", view.pixel_summary.object)
            self.assertIn(
                "No pixels match filters",
                _current_spectrum(view).opts.get().kwargs["title"],
            )
        finally:
            view.cleanup()

    def test_reduced_chi_square_supports_log_view_and_robust_limits(self):
        view = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        try:
            self.assertFalse(view._log_redchi.disabled)
            view._log_redchi.value = True
            image = next(
                element
                for element in _current_map(view)
                if isinstance(element, hv.Image)
            )
            self.assertTrue(image.vdims[0].name.startswith("log10"))
            self.assertIn("clim", image.opts.get().kwargs)

            view.map_select.value = "FitStatus"
            self.assertTrue(view._log_redchi.disabled)
        finally:
            view.cleanup()

    def test_result_view_keeps_its_widgets_out_of_the_plot_block(self):
        view = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=2)
        try:
            # The block is a plain Column now: no collapsible card, no header band.
            self.assertNotIsInstance(view, pn.Card)
            self.assertEqual(view.controls[0], view.map_select)
            self.assertIn(view.layer_selector, view.controls)
            self.assertIn(view.pixel_summary, view.controls)
            self.assertFalse(hasattr(view, "_run_summary"))
            self.assertFalse(
                any(
                    isinstance(control, pn.pane.HTML)
                    and "pixels · method=" in str(control.object)
                    for control in view.controls
                )
            )
            self.assertNotIn("AreaLabel", view.map_select.options.values())
            self.assertNotIn(view.status_filter, view.controls)
            self.assertIn(view.status_filter, view.filter_controls)
            for widget in view.controls:
                self.assertNotIn(widget, view.select())
            for widget in view.filter_controls:
                self.assertNotIn(widget, view.select())
            self.assertEqual(view.run_number, 2)
            self.assertIn("Run 2", view.run_label)
            self.assertIn("cluster_0", view.run_label)
            # Without the card header the run number has to survive in the plots.
            image = next(
                element
                for element in _current_map(view)
                if isinstance(element, hv.Image)
            )
            self.assertIn("Run 2", image.opts.get().kwargs["title"])
            self.assertIn(
                "Run 2", _current_spectrum(view).opts.get().kwargs["title"]
            )
        finally:
            view.cleanup()

    def test_multifit_controls_mount_the_selected_run_below_the_map(self):
        controls = NLLSMultifitControls()
        first = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        second = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=2)
        try:
            self.assertFalse(controls.run_select.visible)

            controls.register(first)
            self.assertEqual(controls.runs, (first,))
            self.assertIs(controls.active_run, first)
            # A single run needs no selector, and the map stays the top control.
            self.assertFalse(controls.run_select.visible)
            self.assertTrue(controls.run_select.disabled)
            mounted = controls._controls_slot.objects
            self.assertEqual(mounted[0], first.map_select)
            self.assertEqual(mounted[1], controls.run_select)
            self.assertEqual(mounted[2], first.controls[1])
            self.assertEqual(mounted[3], first.area_overlay_controls)
            self.assertEqual(mounted[4], controls.filters_button)
            self.assertIsInstance(controls.filters_button, pn.widgets.Button)
            self.assertEqual(controls.filters_button.name, "Filters")
            self.assertEqual(controls.filters_button.button_type, "default")
            self.assertEqual(controls.filters_button.sizing_mode, "stretch_width")
            self.assertEqual(
                controls.filters_button.height,
                first.area_fill_button.height,
            )
            self.assertEqual(
                controls.filters_modal.controls_slot.objects,
                list(first.filter_controls),
            )

            controls.register(second)
            self.assertEqual(controls.runs, (second, first))
            self.assertIs(controls.active_run, second)
            self.assertTrue(controls.run_select.visible)
            self.assertFalse(controls.run_select.disabled)
            mounted = controls._controls_slot.objects
            self.assertEqual(mounted[0], second.map_select)
            self.assertEqual(mounted[1], controls.run_select)
            self.assertEqual(mounted[3], second.area_overlay_controls)
            self.assertEqual(mounted[4], controls.filters_button)
            self.assertNotIn(first.map_select, mounted)
            self.assertEqual(
                controls.filters_modal.controls_slot.objects,
                list(second.filter_controls),
            )

            controls._open_filters(None)
            self.assertTrue(controls.filters_modal.visible)
            second.status_filter.value = [int(FitStatus.SUCCESS)]
            self.assertEqual(
                controls.filters_modal.controls_slot.objects[0].value,
                [int(FitStatus.SUCCESS)],
            )

            controls.run_select.value = first
            mounted = controls._controls_slot.objects
            self.assertEqual(mounted[0], first.map_select)
            self.assertEqual(mounted[1], controls.run_select)
            self.assertEqual(mounted[3], first.area_overlay_controls)
            self.assertEqual(mounted[4], controls.filters_button)
            self.assertNotIn(second.map_select, mounted)
            self.assertEqual(
                controls.filters_modal.controls_slot.objects,
                list(first.filter_controls),
            )
            self.assertIsNotNone(controls.get_root())

            controls.unregister(first)
            self.assertEqual(controls.runs, (second,))
            self.assertIs(controls.active_run, second)
            controls.clear_runs()
            self.assertEqual(controls.runs, ())
            self.assertIsNone(controls.active_run)
            self.assertEqual(controls._controls_slot.objects, [])
            self.assertEqual(controls.filters_modal.controls_slot.objects, [])
        finally:
            first.cleanup()
            second.cleanup()

    def test_result_filters_open_in_the_registered_fitting_modal(self):
        class PageStub:
            def __init__(self):
                self.modal = pn.Column()
                self.opened = False
                self.closed = False

            def open_modal(self):
                self.opened = True

            def close_modal(self):
                self.closed = True

        page = PageStub()
        modal_manager = ModalManager(page)
        layout = FittingRightSidebarLayout(
            FittingModel(),
            custom_page=page,
            modal_manager=modal_manager,
        )
        controls = layout.elemental_multifit_controls
        run = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        derived = NLLSDerivedResultsPlot(_derived_nlls_result(), sequence=1)
        try:
            self.assertTrue(controls.derived_results_button.visible)
            self.assertTrue(controls.derived_results_button.disabled)
            self.assertFalse(controls.derived_results_modal.visible)
            controls.register(run)
            controls._open_filters(None)
            self.assertTrue(page.opened)
            self.assertIn(controls.filters_modal, page.modal.objects)
            self.assertTrue(controls.filters_modal.visible)
            self.assertEqual(
                controls.filters_modal.controls_slot.objects,
                list(run.filter_controls),
            )
            self.assertNotIn(run.status_filter, controls._controls_slot.select())

            controls._open_derived_analyses(None)
            self.assertIn(controls.derived_analyses_modal, page.modal.objects)
            self.assertTrue(controls.derived_analyses_modal.visible)
            self.assertFalse(controls.filters_modal.visible)
            self.assertIn(
                controls.center_a,
                controls.derived_analyses_modal.controls_slot.select(),
            )

            controls.register_derived(derived)
            controls._open_derived_results(None)
            self.assertIn(controls.derived_results_modal, page.modal.objects)
            self.assertTrue(controls.derived_results_modal.visible)
            self.assertFalse(controls.filters_modal.visible)
            self.assertFalse(controls.derived_analyses_modal.visible)
            self.assertIn(
                derived.map_select,
                controls.derived_results_modal.controls_slot.objects,
            )
            self.assertIsNotNone(pn.Row(layout, page.modal).get_root())
        finally:
            controls.unregister_derived(derived)
            derived.cleanup()
            run.cleanup()

    def test_multifit_controls_do_not_expose_modified_model_editor(self):
        controls = NLLSMultifitControls()
        run = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        try:
            controls.register(run)
            self.assertFalse(hasattr(controls, "begin_modified_button"))
            self.assertFalse(hasattr(controls, "rerun_area_select"))
            widget_names = {
                str(widget.name)
                for widget in controls.select(pn.widgets.Widget)
                if getattr(widget, "name", None)
            }
            self.assertNotIn("Begin Modified Model", widget_names)
            self.assertNotIn("Lock All", widget_names)
            self.assertNotIn("Unlock All", widget_names)
        finally:
            run.cleanup()

    def test_derived_analysis_controls_and_plot_follow_the_results_layout(self):
        result = _dense_nlls_result()
        shape = result["FitStatus"].shape
        result["a_elnes_center"] = (("y", "x"), np.full(shape, 1.0))
        result["b_elnes_center"] = (("y", "x"), np.full(shape, 2.0))
        result["a_elnes__component"] = result["BestFit"].copy()
        result["b_elnes__component"] = result["BestFit"].copy() * 0.5
        run = NLLSMultifitResultsPlot(result, run_number=1)
        controls = NLLSMultifitControls()
        derived = NLLSDerivedResultsPlot(_derived_nlls_result(), sequence=1)
        try:
            controls.register(run)
            self.assertTrue(controls.derived_analyses_button.visible)
            self.assertFalse(controls.derived_analyses_button.disabled)
            self.assertEqual(controls.derived_analyses_button.button_type, "default")
            self.assertEqual(
                controls.derived_analyses_button.height,
                controls.derived_results_button.height,
            )
            self.assertNotIn(controls._analysis_controls, controls.objects)
            self.assertFalse(controls.center_button.disabled)
            self.assertFalse(controls.white_button.disabled)
            self.assertNotEqual(controls.center_a.value, controls.center_b.value)
            self.assertNotEqual(controls.white_a.value, controls.white_b.value)
            self.assertEqual(
                controls._center_selectors.objects,
                [controls.center_a, controls.center_b],
            )
            self.assertEqual(
                controls._white_line_selectors.objects,
                [controls.white_a, controls.white_b],
            )
            self.assertEqual(controls._center_selectors.sizing_mode, "stretch_width")
            self.assertEqual(
                controls._white_line_selectors.sizing_mode,
                "stretch_width",
            )

            controls._open_derived_analyses(None)
            self.assertTrue(controls.derived_analyses_modal.visible)
            self.assertEqual(
                controls.derived_analyses_modal.controls_slot.objects,
                [controls._analysis_controls],
            )
            self.assertIn(
                controls.center_a,
                controls.derived_analyses_modal.controls_slot.select(),
            )

            controls.white_mode.value = "manual"
            self.assertTrue(controls.white_window_a.visible)
            self.assertTrue(controls.white_window_b.visible)
            controls.register_derived(derived)
            # Publication must not rebuild a hidden modal: doing so invalidates
            # the same document while the new Bokeh plot is being mounted.
            self.assertEqual(controls._derived_controls_slot.objects, [])
            self.assertTrue(controls.derived_results_button.visible)
            self.assertFalse(controls.derived_results_button.disabled)
            self.assertNotIn(
                derived.map_select,
                controls.derived_analyses_modal.controls_slot.select(),
            )
            controls._open_derived_results(None)
            self.assertTrue(controls.derived_results_modal.visible)
            self.assertIn(
                derived.map_select,
                controls.derived_results_modal.controls_slot.objects,
            )
            self.assertIsInstance(_current_map(derived), hv.Overlay)
            derived_boundaries = tuple(
                element
                for element in _current_map(derived)
                if isinstance(element, hv.Segments)
            )
            self.assertEqual(len(derived_boundaries), 1)
            self.assertGreater(len(derived_boundaries[0].dimension_values("x0")), 4)
            self.assertIsNotNone(derived.get_root())
        finally:
            controls.unregister_derived(derived)
            self.assertTrue(controls.derived_results_button.visible)
            self.assertTrue(controls.derived_results_button.disabled)
            self.assertEqual(
                controls.derived_results_modal.controls_slot.objects,
                [],
            )
            derived.cleanup()
            run.cleanup()

    def test_boundaries_toggle_is_shared_by_runs_and_derived_results(self):
        controls = NLLSMultifitControls()
        first_run = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=1)
        second_run = NLLSMultifitResultsPlot(_dense_nlls_result(), run_number=2)
        first_derived = NLLSDerivedResultsPlot(_derived_nlls_result(), sequence=1)
        later_derived = None
        try:
            controls.register(first_run)
            controls.register(second_run)
            controls.register_derived(first_derived)

            second_run.area_boundaries_button.value = False
            self.assertFalse(first_run.area_boundaries_button.value)
            self.assertFalse(second_run.area_boundaries_button.value)
            self.assertFalse(first_derived.boundaries_visible)
            self.assertFalse(
                any(isinstance(layer, hv.Segments) for layer in _current_map(first_derived))
            )

            # A derived result published after the toggle inherits the same
            # state instead of falling back to always-on boundaries.
            later_derived = NLLSDerivedResultsPlot(_derived_nlls_result(), sequence=2)
            controls.register_derived(later_derived)
            self.assertFalse(later_derived.boundaries_visible)
            self.assertFalse(
                any(isinstance(layer, hv.Segments) for layer in _current_map(later_derived))
            )

            first_run.area_boundaries_button.value = True
            self.assertTrue(first_run.area_boundaries_button.value)
            self.assertTrue(second_run.area_boundaries_button.value)
            self.assertTrue(first_derived.boundaries_visible)
            self.assertTrue(later_derived.boundaries_visible)
            self.assertTrue(
                any(isinstance(layer, hv.Segments) for layer in _current_map(first_derived))
            )
            self.assertTrue(
                any(isinstance(layer, hv.Segments) for layer in _current_map(later_derived))
            )
        finally:
            if later_derived is not None:
                controls.unregister_derived(later_derived)
                later_derived.cleanup()
            controls.unregister_derived(first_derived)
            controls.unregister(second_run)
            controls.unregister(first_run)
            first_derived.cleanup()
            second_run.cleanup()
            first_run.cleanup()

    def test_layout_manager_appends_physically_and_orders_results_visually(self):
        controls = NLLSMultifitControls()
        manager = LayoutManager(
            SimpleNamespace(elemental_multifit_controls=controls),
            SimpleNamespace(),
            FittingModel(),
        )
        source_plot = pn.pane.Markdown(
            "Original plots",
            styles={"order": str(LayoutManager._SOURCE_VISUAL_ORDER)},
        )
        stack = StableAdditiveColumn(
            source_plot,
            sizing_mode="stretch_both",
            min_height=0,
            styles=dict(LayoutManager._ADDITIVE_STACK_STYLES),
        )
        manager._plot_stacks = [stack]
        manager._nlls_result_views = [[]]
        manager._nlls_derived_views = [[]]
        manager._plots_tab = SimpleNamespace(active=0)
        run = manager.add_nlls_result_plot(_dense_nlls_result())
        derived = manager.add_nlls_derived_result_plot(_derived_nlls_result())
        try:
            # Existing DOM children remain a physical prefix. CSS order gives
            # the requested newest-derived -> newest-run -> source display.
            self.assertEqual(stack.objects, [source_plot, run, derived])
            self.assertEqual(
                sorted(stack.objects, key=lambda view: int(view.styles["order"])),
                [derived, run, source_plot],
            )
            self.assertEqual(controls._derived_controls_slot.objects, [])
            controls._open_derived_results(None)
            self.assertIn(
                derived.map_select,
                controls._derived_controls_slot.objects,
            )
        finally:
            manager.clear_nlls_result_plots()
        self.assertEqual(stack.objects, [source_plot])

    def test_additive_plots_keep_existing_geometry_titles_and_scales(self):
        controls = NLLSMultifitControls()
        manager = LayoutManager(
            SimpleNamespace(elemental_multifit_controls=controls),
            SimpleNamespace(),
            FittingModel(),
        )
        reference_plot = hv.Curve(([0.0, 1.0], [2.0, 3.0])).opts(
            title="Reference fit", xlim=(0.0, 1.0), ylim=(2.0, 3.0)
        )
        source_pane = pn.pane.HoloViews(reference_plot, sizing_mode="stretch_both")
        source_plot = pn.Column(
            source_pane,
            min_height=600,
            sizing_mode="stretch_both",
            styles={"order": str(LayoutManager._SOURCE_VISUAL_ORDER)},
        )
        stack = StableAdditiveColumn(
            source_plot,
            sizing_mode="stretch_both",
            min_height=0,
            styles=dict(LayoutManager._ADDITIVE_STACK_STYLES),
        )
        manager._plot_stacks = [stack]
        manager._nlls_result_views = [[]]
        manager._nlls_derived_views = [[]]
        manager._plots_tab = SimpleNamespace(active=0)

        run = manager.add_nlls_result_plot(_dense_nlls_result())
        run_map_model = run.map_pane.object
        run_spectrum_model = run.spectrum_pane.object
        run_map = _current_map(run)
        run_spectrum = _current_spectrum(run)
        reference_options = dict(reference_plot.opts.get().kwargs)
        run_map_options = dict(run_map.opts.get().kwargs)
        run_spectrum_options = dict(run_spectrum.opts.get().kwargs)
        document = Document()
        rendered_stack = stack.get_root(document)
        document.add_root(rendered_stack)
        document_events = []
        document.on_change(document_events.append)
        run_map_models = tuple(
            id(model_and_parent[0]) for model_and_parent in run.map_pane._models.values()
        )
        run_spectrum_models = tuple(
            id(model_and_parent[0]) for model_and_parent in run.spectrum_pane._models.values()
        )
        source_models = tuple(
            id(model_and_parent[0]) for model_and_parent in source_pane._models.values()
        )
        outer_children = tuple(stack.objects)
        outer_model_children = tuple(rendered_stack.children)

        first_analysis = manager.add_nlls_derived_result_plot(_derived_nlls_result())
        second_analysis = manager.add_nlls_derived_result_plot(_derived_nlls_result())
        try:
            self.assertIsNotNone(rendered_stack)
            self.assertIs(source_pane.object, reference_plot)
            self.assertIs(run.map_pane.object, run_map_model)
            self.assertIs(run.spectrum_pane.object, run_spectrum_model)
            self.assertEqual(reference_plot.opts.get().kwargs, reference_options)
            self.assertEqual(run_map.opts.get().kwargs, run_map_options)
            self.assertEqual(run_spectrum.opts.get().kwargs, run_spectrum_options)
            self.assertEqual(
                tuple(id(value[0]) for value in run.map_pane._models.values()),
                run_map_models,
            )
            self.assertEqual(
                tuple(id(value[0]) for value in run.spectrum_pane._models.values()),
                run_spectrum_models,
            )
            self.assertEqual(
                tuple(id(value[0]) for value in source_pane._models.values()),
                source_models,
            )
            self.assertEqual(tuple(stack.objects[: len(outer_children)]), outer_children)
            self.assertEqual(
                stack.objects,
                [source_plot, run, first_analysis, second_analysis],
            )
            self.assertEqual(
                tuple(rendered_stack.children[: len(outer_model_children)]),
                outer_model_children,
            )
            self.assertEqual(
                sorted(stack.objects, key=lambda view: int(view.styles["order"])),
                [second_analysis, first_analysis, run, source_plot],
            )
            outer_event_attrs = [
                event.attr
                for event in document_events
                if getattr(event, "model", None) is rendered_stack
                and hasattr(event, "attr")
            ]
            self.assertEqual(outer_event_attrs, ["children", "children"])
            self.assertEqual(rendered_stack.sizing_mode, "stretch_both")
            self.assertEqual(rendered_stack.min_height, 0)
            self.assertEqual(stack.styles["overflow-y"], "scroll")
            self.assertEqual(stack.styles["scrollbar-gutter"], "stable")
            self.assertEqual(stack.styles["overflow-anchor"], "none")
            self.assertEqual((run.height, run.min_height, run.max_height), (620, 620, 620))
            self.assertEqual(
                (first_analysis.height, first_analysis.min_height, first_analysis.max_height),
                (560, 560, 560),
            )
            self.assertEqual(second_analysis.styles["flex"], "0 0 560px")

            # Publishing derived maps must not detach the live callbacks of the
            # already-rendered NLLS block.
            run.map_select.value = "FitStatus"
            run._tap_stream.event(x=2, y=1)
            self.assertEqual(run.selected_pixel, (1, 2))
            self.assertIn("y=1, x=2", run.pixel_summary.object)
            self.assertIs(run.map_pane.object, run_map_model)
            self.assertIs(run.spectrum_pane.object, run_spectrum_model)
            self.assertEqual(
                tuple(id(value[0]) for value in run.map_pane._models.values()),
                run_map_models,
            )
            self.assertEqual(
                tuple(id(value[0]) for value in run.spectrum_pane._models.values()),
                run_spectrum_models,
            )
        finally:
            manager.clear_nlls_result_plots()
        self.assertEqual(stack.objects, [source_plot])

    def test_one_to_three_derived_registrations_preserve_existing_live_blocks(self):
        """Derived publication is append-only for already rendered live plots.

        This deliberately exercises the sequence that exposed the browser
        regression: a Reference DynamicMap and an NLLS run are rendered first,
        then three derived maps are registered one at a time.  Existing Panel
        and Bokeh models, logical child order, overflow policy, and stream
        subscriptions must survive every registration.
        """
        reference_frames = []

        def reference_frame(x=None, y=None):
            reference_frames.append((x, y))
            offset = 0.0 if x is None else float(x)
            return hv.Curve(([0.0, 1.0], [offset, offset + 1.0])).opts(
                title="Reference fit"
            )

        reference_tap = hv.streams.Tap(x=None, y=None)
        reference_dmap = hv.DynamicMap(
            reference_frame,
            streams=[reference_tap],
        )
        reference_pane = pn.pane.HoloViews(
            reference_dmap,
            sizing_mode="stretch_both",
        )
        reference_block = pn.Column(
            reference_pane,
            min_height=600,
            sizing_mode="stretch_both",
            styles={"order": str(LayoutManager._SOURCE_VISUAL_ORDER)},
        )
        stack = StableAdditiveColumn(
            reference_block,
            sizing_mode="stretch_both",
            min_height=0,
            styles=dict(LayoutManager._ADDITIVE_STACK_STYLES),
        )
        controls = NLLSMultifitControls()
        manager = LayoutManager(
            SimpleNamespace(elemental_multifit_controls=controls),
            SimpleNamespace(),
            FittingModel(),
        )
        manager._plot_stacks = [stack]
        manager._nlls_result_views = [[]]
        manager._nlls_derived_views = [[]]
        manager._plots_tab = SimpleNamespace(active=0)
        run = manager.add_nlls_result_plot(_dense_nlls_result())

        document = Document()
        stack_model = stack.get_root(document)
        document.add_root(stack_model)

        initial_objects = tuple(stack.objects)
        initial_model_children = tuple(stack_model.children)
        initial_run_children = tuple(run.objects)
        initial_reference_children = tuple(reference_block.objects)
        initial_run_tree = tuple(run.select())
        initial_reference_tree = tuple(reference_block.select())
        initial_run_styles = tuple(
            (id(view), dict(getattr(view, "styles", {}) or {}))
            for view in initial_run_tree
        )
        initial_reference_styles = tuple(
            (id(view), dict(getattr(view, "styles", {}) or {}))
            for view in initial_reference_tree
        )
        reference_models = tuple(
            id(model_and_parent[0])
            for model_and_parent in reference_pane._models.values()
        )
        run_map_models = tuple(
            id(model_and_parent[0]) for model_and_parent in run.map_pane._models.values()
        )
        run_spectrum_models = tuple(
            id(model_and_parent[0])
            for model_and_parent in run.spectrum_pane._models.values()
        )
        reference_subscribers = tuple(id(item) for item in reference_tap.subscribers)
        run_subscribers = tuple(id(item) for item in run._tap_stream.subscribers)
        map_dmap = run._map_dmap
        map_pipe = run._map_pipe
        tap_stream = run._tap_stream
        spectrum_dmap = run._spectrum_dmap
        spectrum_pipe = run._spectrum_pipe

        def assert_no_internal_scroll(viewables):
            for view in viewables:
                styles = getattr(view, "styles", {}) or {}
                for key in ("overflow", "overflow-x", "overflow-y"):
                    self.assertNotEqual(
                        str(styles.get(key, "")).lower(),
                        "scroll",
                        f"{type(view).__name__} acquired {key}=scroll",
                    )

        derived_views = []
        click_targets = ((1, 0), (1, 1), (0, 0))
        try:
            self.assertEqual(initial_objects, (reference_block, run))
            self.assertIs(reference_pane.object, reference_dmap)
            self.assertIs(run.map_pane.object, map_dmap)
            self.assertIs(run.spectrum_pane.object, spectrum_dmap)
            self.assertIn(map_pipe, map_dmap.streams)
            self.assertIn(tap_stream, map_dmap.streams)
            self.assertIn(spectrum_pipe, spectrum_dmap.streams)
            assert_no_internal_scroll(initial_reference_tree)
            assert_no_internal_scroll(initial_run_tree)

            for count, (column, row) in enumerate(click_targets, start=1):
                with self.subTest(derived_count=count):
                    derived_views.append(
                        manager.add_nlls_derived_result_plot(_derived_nlls_result())
                    )

                    # Registration may only append.  It must not reorder or
                    # replace any previously published logical/Bokeh child.
                    self.assertEqual(
                        tuple(stack.objects),
                        initial_objects + tuple(derived_views),
                    )
                    self.assertEqual(
                        tuple(stack_model.children[: len(initial_model_children)]),
                        initial_model_children,
                    )
                    self.assertEqual(tuple(run.objects), initial_run_children)
                    self.assertEqual(
                        tuple(reference_block.objects), initial_reference_children
                    )
                    self.assertEqual(tuple(run.select()), initial_run_tree)
                    self.assertEqual(
                        tuple(reference_block.select()), initial_reference_tree
                    )
                    self.assertEqual(
                        tuple(
                            (id(view), dict(getattr(view, "styles", {}) or {}))
                            for view in run.select()
                        ),
                        initial_run_styles,
                    )
                    self.assertEqual(
                        tuple(
                            (id(view), dict(getattr(view, "styles", {}) or {}))
                            for view in reference_block.select()
                        ),
                        initial_reference_styles,
                    )
                    assert_no_internal_scroll(run.select())
                    assert_no_internal_scroll(reference_block.select())

                    self.assertIs(reference_pane.object, reference_dmap)
                    self.assertIs(run.map_pane.object, map_dmap)
                    self.assertIs(run.spectrum_pane.object, spectrum_dmap)
                    self.assertIs(run._map_pipe, map_pipe)
                    self.assertIs(run._tap_stream, tap_stream)
                    self.assertIs(run._spectrum_pipe, spectrum_pipe)
                    self.assertEqual(
                        tuple(
                            id(model_and_parent[0])
                            for model_and_parent in reference_pane._models.values()
                        ),
                        reference_models,
                    )
                    self.assertEqual(
                        tuple(
                            id(model_and_parent[0])
                            for model_and_parent in run.map_pane._models.values()
                        ),
                        run_map_models,
                    )
                    self.assertEqual(
                        tuple(
                            id(model_and_parent[0])
                            for model_and_parent in run.spectrum_pane._models.values()
                        ),
                        run_spectrum_models,
                    )
                    self.assertEqual(
                        tuple(id(item) for item in reference_tap.subscribers),
                        reference_subscribers,
                    )
                    self.assertEqual(
                        tuple(id(item) for item in tap_stream.subscribers),
                        run_subscribers,
                    )

                    # Both the Reference DynamicMap and the NLLS Tap stream
                    # must still react after each additive publication.
                    reference_tap.event(x=count / 10.0, y=count / 20.0)
                    self.assertEqual(
                        reference_frames[-1],
                        (count / 10.0, count / 20.0),
                    )
                    tap_stream.event(x=column, y=row)
                    self.assertEqual(run.selected_pixel, (row, column))
                    self.assertIn(f"y={row}, x={column}", run.pixel_summary.object)
                    self.assertIs(run._map_dmap, map_dmap)
                    self.assertIs(run._spectrum_dmap, spectrum_dmap)
        finally:
            manager.clear_nlls_result_plots()
            reference_tap.clear()

        self.assertEqual(stack.objects, [reference_block])

    def test_tall_and_wide_maps_remain_contained_in_their_result_blocks(self):
        tall_run_result = _dense_nlls_result().isel(
            y=np.resize(np.arange(2), 20)
        ).assign_coords(y=np.arange(20))
        run = NLLSMultifitResultsPlot(tall_run_result, run_number=1)
        tall_derived_result = _derived_nlls_result().isel(
            y=np.resize(np.arange(2), 20)
        ).assign_coords(y=np.arange(20))
        tall_derived = NLLSDerivedResultsPlot(tall_derived_result, sequence=1)
        wide_derived_result = _derived_nlls_result().isel(
            x=np.resize(np.arange(2), 20)
        ).assign_coords(x=np.arange(20))
        wide_derived = NLLSDerivedResultsPlot(wide_derived_result, sequence=2)
        def _figure(pane):
            return next(
                model
                for model in pane.get_root().select({"type": LayoutDOM})
                if type(model).__name__ == "figure"
            )

        def _assert_square_frame(figure):
            self.assertEqual(figure.sizing_mode, "stretch_both")
            self.assertNotEqual(figure.sizing_mode, "scale_both")
            self.assertIsNone(figure.aspect_ratio)
            self.assertTrue(figure.match_aspect)
            self.assertEqual(figure.aspect_scale, 1)
            self.assertIsInstance(figure.x_range, DataRange1d)
            self.assertIsInstance(figure.y_range, DataRange1d)
            self.assertEqual(figure.x_range.range_padding, 0)
            self.assertEqual(figure.y_range.range_padding, 0)
            self.assertFalse(figure.x_range.flipped)
            self.assertTrue(figure.y_range.flipped)

        try:
            self.assertEqual(run.map_pane.sizing_mode, "stretch_both")
            self.assertFalse(hasattr(run.map_pane, "_splitjs_xy_ratio"))
            self.assertIsInstance(run.split, pn.Row)
            self.assertEqual(len(run.split.objects), 3)
            left_column, gutter, right_column = run.split.objects
            self.assertIsInstance(left_column, pn.Column)
            self.assertIsInstance(gutter, DragGutter)
            self.assertIsInstance(right_column, pn.Column)
            self.assertEqual(gutter.width, 10)
            self.assertEqual(gutter.sizing_mode, "stretch_height")
            self.assertEqual(left_column.sizing_mode, "stretch_both")
            self.assertEqual(right_column.sizing_mode, "stretch_both")
            self.assertIn(DragGutter.ROW_CSS_CLASS, run.split.css_classes)
            self.assertIn(DragGutter.PANE_CSS_CLASS, left_column.css_classes)
            self.assertIn(DragGutter.PANE_CSS_CLASS, right_column.css_classes)
            self.assertFalse(run.split.select(SplitJs))
            # Fitting must keep both plots in the native Panel/Bokeh layout
            # tree. A DOM-reparenting SplitJs caused axes and colour bars to
            # detach whenever an additive derived result invalidated the root.
            self.assertEqual(run.map_pane.sizing_mode, "stretch_both")
            self.assertIsNone(run.map_pane.width)
            self.assertIsNone(run.map_pane.height)
            run_figure = _figure(run.map_pane)
            _assert_square_frame(run_figure)
            self.assertIn("Run 1", run_figure.title.text)
            self.assertTrue(run_figure.right)
            self.assertTrue(run_figure.right[0].visible)
            self.assertNotIn("aspect", _current_map(run).opts.get().kwargs)

            for view, expected_title in (
                (tall_derived, "Analysis"),
                (wide_derived, "Analysis"),
            ):
                self.assertEqual(view.map_pane.sizing_mode, "stretch_both")
                figure = _figure(view.map_pane)
                _assert_square_frame(figure)
                self.assertIn(expected_title, figure.title.text)
                self.assertTrue(figure.right)  # colour bar owns its own panel
                self.assertTrue(figure.right[0].visible)
                self.assertNotIn("aspect", _current_map(view).opts.get().kwargs)
        finally:
            wide_derived.cleanup()
            tall_derived.cleanup()
            run.cleanup()

    def test_global_splitjs_contract_remains_available_for_other_pages(self):
        self.assertIn("overflow: auto", SplitJs._CSS_FILE)
        self.assertIn("overflowX = 'hidden'", SplitJs._JS_FILE)
        self.assertNotIn("style.overflow = 'hidden'", SplitJs._JS_FILE)
        self.assertNotIn("window.dispatchEvent", SplitJs._JS_FILE)

    def test_drag_gutter_never_reparents_panes(self):
        """The gutter may resize the panes but must never own them.

        Reparenting is what detached axes and colour bars from their canvas in
        Fitting: Bokeh kept solving the original hierarchy while the browser
        painted another one. Note it was the reparenting, not the messaging:
        the gutter does report the pane box to Python (see the ratio test), and
        that is safe precisely because the panes stay where Panel mounted them.
        """
        source = DragGutter._JS_FILE
        for forbidden in (
            "get_child",       # would make the panes children of this component
            "appendChild",     # would move them out of the Bokeh layout tree
            "removeChild",
            "insertBefore",
            "dispatchEvent",   # would relayout every unrelated responsive plot
            "ResizeObserver",
        ):
            self.assertNotIn(forbidden, source)
        # A plain Python reference, never a Child parameter.
        self.assertNotIn("ratio_pane", DragGutter.param)

        # Panel names its own container div after the class; a second element
        # with that class would be styled as the bar as well.
        self.assertNotIn("'drag-gutter'", source)
        self.assertIn("whateels-drag-gutter", source)
        self.assertIn(DragGutter.ROW_CSS_CLASS, source)
        self.assertIn(DragGutter.PANE_CSS_CLASS, source)
        # Panel renders each layout child inside its own shadow root, so the
        # row is only reachable by stepping out through the shadow hosts.
        self.assertIn("current.host", source)

    def test_drag_gutter_resolves_the_stale_layout_it_leaves_behind(self):
        """Changing flex is invisible to a plot that sizes its own box.

        A scale_* figure keeps the geometry of its first solve because its own
        observed element never changed - only the parent that clips it. The map
        then stays frozen at the old size until an unrelated window resize wakes
        the page, which is the bug this guards. The gutter therefore invalidates
        one cached view from the split at a bounded cadence during movement.
        On release it cancels any intermediate frame and replaces it with one
        final pass for the last pointer position.
        """
        source = DragGutter._JS_FILE
        self.assertIn("invalidate_layout", source)
        self.assertIn("requestAnimationFrame", source)
        self.assertIn("const RELAYOUT_INTERVAL_MS = 50", source)
        # The view-tree walk is lazy and cached across complete gestures.
        self.assertIn("views_inside", source)
        self.assertIn("is_inside", source)
        self.assertIn("let relayout_view = null", source)
        self.assertIn("resolve_relayout_view()", source)
        self.assertNotIn("resolve_relayout_view(false)", source)
        self.assertIn("solve_again(view)", source)
        # Exactly one invocation: never one call per pane.
        self.assertEqual(source.count("solve_again("), 1)
        self.assertNotIn("for (const view of views_inside", source)
        # Pointer bursts are reduced to the last position of each paint frame.
        self.assertIn("schedule_drag", source)
        drag_handler = source.split("'pointermove'")[-1].split("'pointerup'")[0]
        self.assertIn("schedule_drag(", drag_handler)
        self.assertNotIn("getBoundingClientRect", drag_handler)
        drag_flush = source.split("const flush_drag_frame")[1].split(
            "const schedule_drag"
        )[0]
        self.assertIn("apply_ratio(ratio)", drag_flush)
        self.assertIn("if (dragging)", drag_flush)
        self.assertIn("request_relayout(false)", drag_flush)
        self.assertIn("ratio_box_width = available_width * ratio", drag_flush)
        self.assertIn("ratio_resize_pending = true", drag_flush)
        self.assertNotIn("report_geometry", drag_flush)
        self.assertNotIn("getBoundingClientRect", drag_flush)
        stop_handler = source.split("const stop_drag")[1].split(
            "gutter.addEventListener('pointerdown'"
        )[0]
        self.assertIn("flush_pending_drag()", stop_handler)
        self.assertIn("cancel_pending_relayout()", stop_handler)
        self.assertLess(
            stop_handler.index("dragging = false"),
            stop_handler.index("flush_pending_drag()"),
        )
        self.assertEqual(stop_handler.count("report_geometry()"), 1)
        self.assertEqual(stop_handler.count("request_relayout(true)"), 1)
        self.assertIn("model.on('remove'", source)
        self.assertIn("removeEventListener('resize'", source)
        # Elemental NLLS normally keeps overflow visible so axes and colour bars
        # survive additive publication. Only the active gesture may clip it,
        # and the original inline value is restored after the final solve.
        self.assertIn("guard_pane_overflow()", source)
        self.assertIn("restore_overflow_after_relayout = true", source)
        self.assertIn("restore_pane_overflow()", source)
        self.assertIn("style.overflow = 'hidden'", source)
        # The cheap global alternative stays banned - it would relayout every
        # responsive plot stacked above this split.
        self.assertNotIn("dispatchEvent", source)

    def test_drag_gutter_keeps_the_ratio_by_giving_height_back(self):
        """Fill the height, then trade height for ratio once width binds.

        The durable fit is SplitJs._apply_left_plot_pixel_ratio's. During the
        gesture the same fit is applied to the browser-side Bokeh model in one
        unsynchronised update; release reports the exact box so Python retains
        the final dimensions. Plain DOM sizing remains invalid because Bokeh's
        next solve would overwrite it.
        """
        pane = pn.pane.HoloViews(hv.Curve([]))
        gutter = DragGutter(ratio_pane=pane, pane_ratio=0.6)
        self.assertIn(DragGutter.RATIO_PANE_CSS_CLASS, pane.css_classes)
        dimension_update_batches = []
        pane.param.watch(
            lambda *events: dimension_update_batches.append(events),
            ["sizing_mode", "width", "height"],
        )

        # Wide pane: height is the binding side, so the height is taken whole.
        gutter._handle_msg({"width": 800, "height": 600})
        self.assertEqual(pane.height, 592)               # 600 minus the margin
        self.assertAlmostEqual(pane.width / pane.height, 0.6, places=2)
        self.assertEqual(pane.sizing_mode, "fixed")
        self.assertEqual(len(dimension_update_batches), 1)
        self.assertEqual(len(dimension_update_batches[0]), 3)
        self.assertIsNone(pane.min_width)
        self.assertIsNone(pane.max_width)
        self.assertIsNone(pane.min_height)
        self.assertIsNone(pane.max_height)

        # Dragging the gutter left makes width the binding side. The height
        # must shrink; keeping it would squash the map, which is the bug.
        gutter._handle_msg({"width": 200, "height": 600})
        self.assertLess(pane.height, 592)
        self.assertAlmostEqual(pane.width / pane.height, 0.6, places=2)
        self.assertLessEqual(pane.width, 200)
        self.assertLessEqual(pane.height, 600)
        self.assertEqual(len(dimension_update_batches), 2)
        self.assertEqual(
            {event.name for event in dimension_update_batches[1]},
            {"width", "height"},
        )
        # A different map shape re-fits without waiting for the next drag.
        gutter.pane_ratio = 2.0
        gutter._handle_msg({"width": 800, "height": 600})
        self.assertAlmostEqual(pane.width / pane.height, 2.0, places=2)

        # Zero ratio disables the sizing entirely: plain flex, as before.
        untouched = pn.pane.HoloViews(hv.Curve([]))
        DragGutter(ratio_pane=untouched)._handle_msg({"width": 800, "height": 600})
        self.assertIsNone(untouched.width)

        source = DragGutter._JS_FILE
        # Intermediate boxes never cross the websocket. The marked Bokeh model
        # receives one local setv and release sends the exact final geometry.
        drag_flush = source.split("const flush_drag_frame")[1].split(
            "const schedule_drag"
        )[0]
        self.assertNotIn("report_geometry", drag_flush)
        self.assertNotIn("REPORT_INTERVAL_MS", source)
        self.assertIn("view_with_class_inside", source)
        self.assertIn("target.setv(", source)
        self.assertIn("{ sync: false }", source)
        self.assertIn("const FIT_MARGIN = 8", source)
        self.assertIn("last_reported_width", source)
        # Only the exact final box is read from the DOM on release.
        self.assertNotIn("getBoundingClientRect", drag_flush)
        stop_handler = source.split("const stop_drag")[1].split(
            "gutter.addEventListener('pointerdown'"
        )[0]
        self.assertLess(
            stop_handler.index("flush_pending_drag()"),
            stop_handler.index("report_geometry()"),
        )

        gutter = DragGutter()
        self.assertEqual(gutter.width, 10)
        self.assertEqual(gutter.sizing_mode, "stretch_height")
        self.assertEqual(gutter.margin, 0)
        self.assertEqual(gutter.min_pane_size, 160)
        # No Child parameters at all: the component cannot hold a pane.
        self.assertFalse([
            name for name, parameter in gutter.param.objects().items()
            if type(parameter).__name__ == "Child"
        ])

        row = pn.Row(
            pn.Column(css_classes=[DragGutter.PANE_CSS_CLASS]),
            gutter,
            pn.Column(css_classes=[DragGutter.PANE_CSS_CLASS]),
            css_classes=[DragGutter.ROW_CSS_CLASS],
        )
        root = row.get_root(Document())
        left_model, gutter_model, right_model = root.children
        self.assertEqual(root.css_classes, [DragGutter.ROW_CSS_CLASS])
        self.assertEqual(left_model.css_classes, [DragGutter.PANE_CSS_CLASS])
        self.assertEqual(right_model.css_classes, [DragGutter.PANE_CSS_CLASS])
        self.assertEqual(gutter_model.width, 10)
        self.assertEqual(gutter_model.class_name, "DragGutter")
        # Custom params travel on the inner data model, which is what the ESM
        # proxy reads; a plain attribute on the outer model would stay unset.
        self.assertEqual(gutter_model.data.min_pane_size, 160)

    def test_layout_manager_publishes_run_controls_to_the_results_tab(self):
        layout = FittingRightSidebarLayout(FittingModel())
        controls = layout.elemental_multifit_controls
        manager = LayoutManager(
            SimpleNamespace(elemental_multifit_controls=controls),
            SimpleNamespace(),
            FittingModel(),
        )
        source_plot = pn.pane.Markdown(
            "Original plots",
            styles={"order": str(LayoutManager._SOURCE_VISUAL_ORDER)},
        )
        manager._plot_stacks = [
            StableAdditiveColumn(
                source_plot,
                sizing_mode="stretch_both",
                min_height=0,
            )
        ]
        manager._nlls_result_views = [[]]
        manager._nlls_derived_views = [[]]
        manager._plots_tab = SimpleNamespace(active=0)

        first = manager.add_nlls_result_plot(_dense_nlls_result())
        second = manager.add_nlls_result_plot(_dense_nlls_result())
        self.assertEqual(controls.runs, (second, first))
        self.assertIs(controls.active_run, second)

        manager.clear_nlls_result_plots()
        self.assertEqual(controls.runs, ())
        self.assertIsNone(controls.active_run)

    def test_layout_manager_appends_runs_without_replacing_older_plots(self):
        manager = LayoutManager(SimpleNamespace(), SimpleNamespace(), FittingModel())
        source_plot = pn.pane.Markdown(
            "Original plots",
            styles={"order": str(LayoutManager._SOURCE_VISUAL_ORDER)},
        )
        stack = StableAdditiveColumn(
            source_plot,
            sizing_mode="stretch_both",
            min_height=0,
        )
        manager._plot_stacks = [stack]
        manager._nlls_result_views = [[]]
        manager._nlls_derived_views = [[]]
        manager._plots_tab = SimpleNamespace(active=0)
        first = manager.add_nlls_result_plot(_dense_nlls_result())
        second = manager.add_nlls_result_plot(_dense_nlls_result())
        try:
            self.assertEqual(stack.objects, [source_plot, first, second])
            self.assertEqual(
                sorted(stack.objects, key=lambda view: int(view.styles["order"])),
                [second, first, source_plot],
            )
            self.assertEqual(manager.nlls_result_views, (second, first))
            self.assertEqual(first._run_number, 1)
            self.assertEqual(second._run_number, 2)
            self.assertIsNotNone(stack.get_root())
            # Each run owns its gutter and its marked row, so dragging one run's
            # separator cannot reach the panes of another run or of the source.
            gutters = [run.split.objects[1] for run in (first, second)]
            self.assertTrue(all(isinstance(g, DragGutter) for g in gutters))
            self.assertIsNot(gutters[0], gutters[1])
            for run in (first, second):
                self.assertIn(DragGutter.ROW_CSS_CLASS, run.split.css_classes)
                self.assertEqual(
                    [
                        pane.css_classes
                        for pane in (run.split.objects[0], run.split.objects[2])
                    ],
                    [[DragGutter.PANE_CSS_CLASS], [DragGutter.PANE_CSS_CLASS]],
                )
        finally:
            manager.clear_nlls_result_plots()
        self.assertEqual(stack.objects, [source_plot])


class ElementalReferenceControllerTests(unittest.TestCase):
    class FakeProvider:
        @staticmethod
        def available_edges(atomic_number):
            return ("K1",)

        @staticmethod
        def element_info(atomic_number):
            if int(atomic_number) == 1:
                return "Hydrogen", "H"
            return "Helium", "He"

        @staticmethod
        def load_raw(atomic_number, shell):
            return SimpleNamespace(shell=shell, onset_eV=2.0)

        @staticmethod
        def curve(
            atomic_number,
            shells,
            geometry,
            eloss,
            broadening,
            fit_range,
        ):
            energy = np.asarray(eloss, dtype=float)
            shape = np.exp(-0.5 * ((energy - 5.0) / 1.0) ** 2)
            _, symbol = ElementalReferenceControllerTests.FakeProvider.element_info(
                atomic_number
            )
            return OOSCurveSnapshot(
                energy_eV=energy,
                normalized_shape=shape,
                physical_shape=shape,
                normalization_factor=1.0,
                units=OOS_UNITS,
                formula_version=OOS_FORMULA_VERSION,
                provider_version=OOS_PROVIDER_VERSION,
                atomic_number=int(atomic_number),
                symbol=symbol,
                shells=tuple(shells),
                onsets_eV=tuple(2.0 for _ in shells),
                table_checksums=tuple("test" for _ in shells),
                broadening_sigma_eV=float(broadening.sigma_eV),
                fit_range=fit_range,
            )

    def setUp(self) -> None:
        self.eloss = np.linspace(0.0, 10.0, 101)
        self.base_shape = np.exp(-0.5 * ((self.eloss - 5.0) / 1.0) ** 2)
        self.labels = np.array([[0, 0, 1], [0, 0, 1]])
        amplitudes = np.where(self.labels == 0, 2.0, 4.0)
        cube = amplitudes[..., None] * self.base_shape[None, None, :]
        raw = xr.Dataset(
            {"ElectronCount": (("y", "x", "Eloss"), cube)},
            coords={"y": np.arange(2), "x": np.arange(3), "Eloss": self.eloss},
            attrs={
                "original_name": "synthetic.dm4",
                "image_name": "synthetic",
                "beam_energy": 200.0,
                "collection_angle": 20.0,
                "convergence_angle": 0.0,
            },
        )
        self.dataset = publish_power_law_subtracted_dataset(
            raw, raw["ElectronCount"], fit_range_eV=(0.0, 1.0)
        )
        self.state = AppState()
        self.state.plot_dataset = self.dataset
        self.state.preprocessed_plot_dataset = self.dataset
        self.state.selected_tab_index_dataset = 0
        self.state.last_clustering_result = {
            "clustering": {
                "file": "synthetic.dm4",
                "spectrum_image": "synthetic",
                "type": "K-Means",
                "inputs": {"n_clusters": 2},
                "outputs": {
                    "labels": self.labels,
                    "centres": np.zeros((2, self.eloss.size)),
                },
            }
        }
        self.layout = FittingRightSidebarLayout(FittingModel())
        self.layout.fitting_tabs.active = 1
        self.visualizer = SimpleNamespace(
            _region_pairs=[(0, 0), (1, 0)],
            main_result_plot=None,
            clustering_payload=None,
            edge_preview_payload=None,
            edge_preview_updates=[],
        )
        self.visualizer.show_nlls_reference_result = (
            lambda plot: setattr(self.visualizer, "main_result_plot", plot)
        )
        self.visualizer.clear_nlls_reference_result = (
            lambda: setattr(self.visualizer, "main_result_plot", None)
        )
        self.visualizer.show_nlls_clustering = (
            lambda labels, energy, spectra: setattr(
                self.visualizer,
                "clustering_payload",
                (np.asarray(labels), np.asarray(energy), spectra),
            )
        )
        self.visualizer.clear_nlls_clustering = (
            lambda: setattr(self.visualizer, "clustering_payload", None)
        )

        def show_edge_preview(
            energy,
            spectrum,
            curves,
            *,
            spectrum_label="Spectrum",
            scale_bases=None,
        ):
            payload = (
                np.asarray(energy, dtype=float),
                np.asarray(spectrum, dtype=float),
                tuple(
                    (
                        str(label),
                        np.asarray(curve_x, dtype=float),
                        np.asarray(curve_y, dtype=float),
                    )
                    for label, curve_x, curve_y in curves
                ),
                str(spectrum_label),
            )
            self.visualizer.edge_preview_payload = payload
            self.visualizer.edge_preview_updates.append(payload)

        self.visualizer.show_nlls_edge_preview = show_edge_preview
        self.visualizer.clear_nlls_edge_preview = (
            lambda: setattr(self.visualizer, "edge_preview_payload", None)
        )
        self.published_multifit_results = []
        self.published_derived_results = []
        parent = SimpleNamespace(
            layout=SimpleNamespace(
                _chosen_visualizers=[self.visualizer],
                add_nlls_result_plot=self.published_multifit_results.append,
                add_nlls_derived_result_plot=self.published_derived_results.append,
            )
        )
        self.controller = NLLSController(
            parent, self.layout, self.state, provider=self.FakeProvider()
        )
        self.layout.elemental_input["model_composition"].value = "continuum_only"
        self.layout.elemental_input["subshells"].value = ["K1"]
        self.controller._on_add_edge(None)
        self.controller._on_build_model(None)

    def tearDown(self) -> None:
        self.controller.cleanup()

    @staticmethod
    def _amplitude(snapshot):
        return next(
            float(parameter["value"])
            for parameter in snapshot.params
            if str(parameter["name"]).endswith("_A")
        )

    def test_subshell_catalog_keeps_shell_values_and_attaches_onset_labels(self):
        widget = self.layout.elemental_input["subshells"]
        stylesheet = "\n".join(str(item) for item in widget.stylesheets)

        self.assertEqual(widget.options, ["K1"])
        self.assertEqual(widget.value, ["K1"])
        self.assertIn('data-value="K1"', stylesheet)
        self.assertIn('--subshell-onset: "2 eV"', stylesheet)

    def test_edge_preview_reacts_to_shift_and_updates_the_saved_definition(self):
        payload = self.visualizer.edge_preview_payload
        self.assertIsNotNone(payload)
        preview_energy, preview_spectrum, curves, spectrum_label = payload
        self.assertEqual(spectrum_label, "ROI mean (2 pixels)")
        np.testing.assert_allclose(preview_energy, self.eloss)
        np.testing.assert_allclose(preview_spectrum, 2.0 * self.base_shape)
        self.assertEqual(len(curves), 1)
        initial_label, initial_x, initial_y = curves[0]
        self.assertIn("H K1 OOS", initial_label)
        self.assertIn("shift +0 eV", initial_label)
        self.assertAlmostEqual(initial_x[np.nanargmax(initial_y)], 5.0)
        self.assertTrue(self.controller.workspace.is_area_built("default"))

        update_count = len(self.visualizer.edge_preview_updates)
        self.layout.elemental_input["chemical_shift"].value = 1.0

        continuum = self.controller.workspace.areas["default"].continuum_specs[0]
        self.assertEqual(continuum.chemical_shift.value, 1.0)
        self.assertFalse(self.controller.workspace.is_area_built("default"))
        self.assertGreater(len(self.visualizer.edge_preview_updates), update_count)
        _, _, shifted_curves, _ = self.visualizer.edge_preview_payload
        shifted_label, shifted_x, shifted_y = shifted_curves[0]
        self.assertIn("shift +1 eV", shifted_label)
        np.testing.assert_allclose(shifted_x, initial_x)
        self.assertAlmostEqual(shifted_x[np.nanargmax(shifted_y)], 4.0)

    def test_elnes_initial_centers_use_each_subshell_local_peak(self):
        """A doublet must not initialise both Gaussians on the higher line."""
        energy = np.array(
            [454.0, 455.184, 457.0, 459.324, 460.0, 461.223, 462.0, 464.673, 467.0]
        )
        intensity = np.array([0.0, 0.1, 1.0, 1.9, 0.5, 0.2, 1.0, 2.6, 0.4])

        l3_offset = self.controller._initial_elnes_center_offset(
            energy, intensity, 455.184, 461.223
        )
        l2_offset = self.controller._initial_elnes_center_offset(
            energy, intensity, 461.223, None
        )

        self.assertAlmostEqual(l3_offset, 4.14, places=2)
        self.assertAlmostEqual(l2_offset, 3.45, places=2)

    def test_chemical_shift_moves_the_associated_elnes_in_the_live_preview(self):
        self.layout.elemental_input["model_composition"].value = (
            "continuum_plus_elnes"
        )
        self.layout.elemental_input["chemical_shift"].value = 1.0

        fine = self.controller.workspace.areas["default"].fine_structure_specs[0]
        # The initial center is the local maximum (5 eV), i.e. 3 eV above
        # the unshifted onset.  A chemical shift moves that entire relation.
        self.assertEqual(fine.offset_from_onset.value, 3.0)
        self.assertEqual(fine.offset_from_onset.minimum, 0.0)
        self.assertEqual(fine.offset_from_onset.maximum, 14.0)
        _, _, curves, _ = self.visualizer.edge_preview_payload
        label, energy, values = next(curve for curve in curves if "Gaussian" in curve[0])
        self.assertIn("center 4 eV", label)
        self.assertAlmostEqual(energy[np.argmax(values)], 4.0, places=1)

    def test_add_edge_initializes_elnes_from_the_local_peak(self):
        """A new ELNES uses the local peak relative to its shifted onset."""
        edge = self.controller.workspace.areas["default"].edges[0]
        self.controller.workspace.remove_edge("default", edge.id)
        self.layout.elemental_input["chemical_shift"].value = 1.0

        self.controller._on_add_edge(None)

        area = self.controller.workspace.areas["default"]
        self.assertEqual(area.continuum_specs[0].chemical_shift.value, 1.0)
        offset = area.fine_structure_specs[0].offset_from_onset
        self.assertEqual(offset.value, 4.0)
        self.assertEqual(offset.minimum, 0.0)
        self.assertEqual(offset.maximum, 14.0)

    def test_continuum_card_edits_once_with_matching_shift_bounds(self):
        # The layout's model normally shares this state through CacheManager.
        # Use the isolated controller state explicitly in this regression fixture.
        self.layout._model._app_state = self.state
        editor = self.layout.elemental_model_editor
        editor.refresh()
        continuum = self.controller.workspace.areas["default"].continuum_specs[0]
        shift_widgets = editor.parameter_widgets[
            (continuum.id, "chemical_shift")
        ]
        shift_input = shift_widgets["value"]

        self.assertEqual(shift_widgets["minimum"].value, -20.0)
        self.assertEqual(shift_widgets["maximum"].value, 20.0)
        self.assertEqual(shift_widgets["value"].format, "0.00")
        self.assertEqual(shift_widgets["minimum"].format, "0.00")
        self.assertEqual(shift_widgets["maximum"].format, "0.00")
        revision = self.state.nlls_revision
        shift_input.value = 1.0

        self.assertEqual(self.state.nlls_revision, revision + 1)
        continuum = self.controller.workspace.areas["default"].continuum_specs[0]
        self.assertEqual(continuum.chemical_shift.value, 1.0)
        fine = self.controller.workspace.areas["default"].fine_structure_specs[0]
        self.assertEqual(fine.offset_from_onset.value, 3.0)
        self.assertEqual(
            editor.parameter_widgets[(fine.id, "offset_from_onset")]["value"].value,
            4.0,
        )
        self.assertEqual(editor._onset_readouts[fine.id].value, "Shifted onset: 1.00 eV")

        # The card shows absolute energy, even after a shift. Its next edit
        # must still persist the correct onset-relative model parameter.
        editor.parameter_widgets[(fine.id, "offset_from_onset")]["value"].value = 5.0
        updated = self.controller.workspace.areas["default"].fine_structure_specs[0]
        self.assertEqual(updated.offset_from_onset.value, 4.0)

        shift_input.value = 21.0
        self.assertEqual(shift_input.value, 1.0)
        self.assertEqual(self.state.nlls_revision, revision + 2)

    def test_model_cards_select_one_component_with_compact_parameter_rows(self):
        self.layout._model._app_state = self.state
        self.layout.elemental_input["element_atomic_number"].value = 2
        self.controller._on_add_edge(None)
        editor = self.layout.elemental_model_editor
        editor.refresh()
        area = self.controller.workspace.areas["default"]
        first_continuum, second_continuum = area.continuum_specs
        second_fine = next(
            component
            for component in area.fine_structure_specs
            if component.edge_id == second_continuum.edge_id
        )

        self.assertIs(editor._continuum_body.objects[0], editor._continuum_selector_row)
        self.assertIs(editor._continuum_selector_row.objects[0], editor.continuum_selector)
        self.assertGreaterEqual(editor._continuum_selector_row.min_height, 38)
        self.assertEqual(editor._continuum_selector_row.margin, (0, 0, 5, 0))
        self.assertEqual(len(editor.continuum_selector.options), 2)
        self.assertEqual(len(editor.elnes_selector.options), 2)
        self.assertEqual(editor.continuum_selector.sizing_mode, "stretch_width")
        self.assertEqual(editor.continuum_selector.stylesheets, [])
        self.assertEqual(editor._continuum_form.styles["background"], "transparent")

        def assert_parameter_block(block, widgets, label, margin):
            header, numeric_fields = block.objects
            self.assertEqual(header.objects[0].value, label)
            self.assertEqual(header.objects[-2].value, "Flexibility")
            self.assertIs(header.objects[-1], widgets["vary"])
            self.assertEqual(block.margin, margin)
            self.assertEqual(block.styles["gap"], "8px")
            self.assertEqual(len(numeric_fields.objects), 3)
            self.assertIs(numeric_fields.objects[0], widgets["value"])
            self.assertIs(numeric_fields.objects[1], widgets["minimum"])
            self.assertIs(numeric_fields.objects[2], widgets["maximum"])
            for numeric_widget in numeric_fields.objects:
                self.assertEqual(numeric_widget.format, "0.00")
                self.assertEqual(numeric_widget.step, 0.01)

        first_amplitude = editor.parameter_widgets[(first_continuum.id, "amplitude")]
        first_shift = editor.parameter_widgets[(first_continuum.id, "chemical_shift")]
        assert_parameter_block(
            editor._continuum_form.objects[0],
            first_amplitude,
            "Amplitude",
            (0, 0, 10, 0),
        )
        assert_parameter_block(
            editor._continuum_form.objects[1],
            first_shift,
            "Chemical shift (eV)",
            (0, 0, 10, 0),
        )

        editor.continuum_selector.value = second_continuum.id
        self.assertNotIn(
            (first_continuum.id, "amplitude"), editor.parameter_widgets
        )
        second_amplitude = editor.parameter_widgets[
            (second_continuum.id, "amplitude")
        ]
        second_amplitude["value"].value = 3.0
        self.assertEqual(
            self.controller.workspace.areas["default"].continuum_specs[1].amplitude.value,
            3.0,
        )

        editor.elnes_selector.value = second_fine.id
        self.assertIn(second_fine.id, editor.fine_structure_widgets)
        self.assertIn(
            (second_fine.id, "offset_from_onset"), editor.parameter_widgets
        )
        fine_controls = editor.fine_structure_widgets[second_fine.id]
        self.assertIsInstance(fine_controls["enabled"], pn.widgets.Switch)
        self.assertEqual(
            fine_controls["enabled"].styles["transform"], "translateY(5px)"
        )
        self.assertIs(editor._elnes_body.objects[0], editor._elnes_form)
        self.assertIs(editor._elnes_selector_row.objects[0], editor.elnes_selector)
        self.assertIs(editor._elnes_selector_row.objects[1], fine_controls["enabled"])
        self.assertEqual(fine_controls["enabled"].name, "")
        self.assertEqual(
            editor._elnes_selector_row.styles["align-items"], "center"
        )
        self.assertIsInstance(editor._elnes_shape_row, pn.Column)
        self.assertEqual(editor._elnes_shape_row.objects, [fine_controls["shape"]])
        self.assertGreaterEqual(editor._elnes_shape_row.min_height, 76)
        self.assertEqual(editor._elnes_shape_row.margin, (0, 0, 10, 0))
        self.assertEqual(editor._elnes_selector_row.margin, (0, 0, 10, 0))
        self.assertEqual(fine_controls["shape"].sizing_mode, "stretch_width")
        self.assertEqual(fine_controls["shape"].stylesheets, [])
        parameter_editor = editor._elnes_form.objects[2]
        self.assertEqual(parameter_editor.objects[0].value, "Shifted onset: 2.00 eV")
        assert_parameter_block(
            parameter_editor.objects[1],
            editor.parameter_widgets[(second_fine.id, "offset_from_onset")],
            "Center (eV)",
            (0, 0, 10, 0),
        )
        assert_parameter_block(
            parameter_editor.objects[2],
            editor.parameter_widgets[(second_fine.id, "sigma")],
            "Sigma (eV)",
            (0, 0, 10, 0),
        )
        assert_parameter_block(
            parameter_editor.objects[3],
            editor.parameter_widgets[(second_fine.id, "amplitude")],
            "Amplitude",
            (0, 0, 10, 0),
        )
        fine_controls["enabled"].value = False
        self.assertFalse(
            next(
                item
                for item in self.controller.workspace.areas["default"].fine_structure_specs
                if item.id == second_fine.id
            ).enabled
        )
        editor.refresh()
        self.assertEqual(editor.continuum_selector.value, second_continuum.id)
        self.assertEqual(editor.elnes_selector.value, second_fine.id)

    def test_edges_modal_keeps_each_card_toggle_and_edit_controls_independent(self):
        self.layout._model._app_state = self.state
        self.layout.elemental_input["element_atomic_number"].value = 2
        self.controller._on_add_edge(None)
        modal = self.layout.edge_added_modal
        modal.refresh()

        self.assertIn("Edges Added", modal._title_pane.object)
        self.assertEqual(modal._close_button.name, "Close")
        self.assertEqual(modal._close_button.button_type, "success")
        first_card, second_card = modal._body.objects
        first_toggle = first_card.objects[0].objects[0]
        first_details = first_card.objects[1]
        second_details = second_card.objects[1]
        first_toggle.clicks += 1

        self.assertFalse(first_details.visible)
        self.assertTrue(second_details.visible)
        self.assertEqual(first_card.objects[0].styles["margin"], "0")
        self.assertEqual(first_card.styles["padding"], "0")

        self.controller._active_run_request = object()
        self.controller._refresh_button_states()
        try:
            card = modal._body.objects[0]
            self.assertTrue(card.objects[0].objects[1].disabled)
            editor = self.layout.elemental_model_editor
            self.assertTrue(
                all(
                    widget.disabled
                    for widgets in editor.parameter_widgets.values()
                    for widget in widgets.values()
                )
            )
            self.assertTrue(
                all(
                    widget.disabled
                    for widgets in editor.fine_structure_widgets.values()
                    for widget in widgets.values()
                )
            )
        finally:
            self.controller._active_run_request = None
            self.controller._refresh_button_states()

    def test_advanced_model_editor_updates_gaussian_and_live_spectrum_preview(self):
        self.layout._model._app_state = self.state
        self.layout.elemental_input["model_composition"].value = (
            "continuum_plus_elnes"
        )
        editor = self.layout.elemental_model_editor
        editor.refresh()
        self.assertIsNotNone(self.layout.elemental_continuum_section.get_root(Document()))
        self.assertIsNotNone(self.layout.elemental_elnes_section.get_root(Document()))
        area = self.controller.workspace.areas["default"]
        fine = area.fine_structure_specs[0]

        offset = editor.parameter_widgets[(fine.id, "offset_from_onset")]
        sigma = editor.parameter_widgets[(fine.id, "sigma")]
        amplitude = editor.parameter_widgets[(fine.id, "amplitude")]
        initial_revision = self.state.nlls_revision

        offset["value"].value = 6.0
        sigma["value"].value = 0.75
        amplitude["value"].value = 2.0
        amplitude["vary"].value = False

        updated = self.controller.workspace.areas["default"].fine_structure_specs[0]
        self.assertEqual(updated.offset_from_onset.value, 4.0)
        self.assertEqual(updated.sigma.value, 0.75)
        self.assertEqual(updated.amplitude.value, 2.0)
        self.assertFalse(updated.amplitude.vary)
        self.assertFalse(self.controller.workspace.is_area_built("default"))
        self.assertGreater(self.state.nlls_revision, initial_revision)

        _, _, curves, _ = self.visualizer.edge_preview_payload
        gaussian_label, gaussian_x, gaussian_y = next(
            curve for curve in curves if "Gaussian" in curve[0]
        )
        self.assertIn("center 6 eV", gaussian_label)
        self.assertAlmostEqual(gaussian_x[np.argmax(gaussian_y)], 6.0, places=1)
        self.assertGreater(float(np.max(gaussian_y)), 0.0)

        revision = self.state.nlls_revision
        offset["minimum"].value = 7.0
        self.assertEqual(offset["minimum"].value, 2.0)
        self.assertEqual(self.state.nlls_revision, revision)
        self.assertTrue(editor._elnes_error.visible)

    def test_advanced_model_editor_updates_continuum_bounds_and_elnes_shape(self):
        self.layout._model._app_state = self.state
        editor = self.layout.elemental_model_editor
        editor.refresh()
        area = self.controller.workspace.areas["default"]
        continuum = area.continuum_specs[0]
        fine = area.fine_structure_specs[0]

        continuum_amplitude = editor.parameter_widgets[(continuum.id, "amplitude")]
        continuum_amplitude["value"].value = 3.0
        continuum_amplitude["maximum"].value = 8.0
        continuum_amplitude["vary"].value = False
        fine_controls = editor.fine_structure_widgets[fine.id]
        fine_controls["shape"].value = "LorentzianModel"
        fine_controls["enabled"].value = False

        updated_area = self.controller.workspace.areas["default"]
        updated_continuum = updated_area.continuum_specs[0]
        updated_fine = updated_area.fine_structure_specs[0]
        self.assertEqual(updated_continuum.amplitude.value, 3.0)
        self.assertEqual(updated_continuum.amplitude.maximum, 8.0)
        self.assertFalse(updated_continuum.amplitude.vary)
        self.assertEqual(updated_fine.shape, "LorentzianModel")
        self.assertFalse(updated_fine.enabled)

    def test_edge_preview_is_scoped_to_the_elemental_tab(self):
        self.assertIsNotNone(self.visualizer.edge_preview_payload)

        self.layout.fitting_tabs.active = 0
        self.assertIsNone(self.visualizer.edge_preview_payload)
        update_count = len(self.visualizer.edge_preview_updates)

        self.layout.elemental_input["chemical_shift"].value = 0.5
        self.assertIsNone(self.visualizer.edge_preview_payload)
        self.assertEqual(len(self.visualizer.edge_preview_updates), update_count)

        self.layout.fitting_tabs.active = 1
        self.assertIsNotNone(self.visualizer.edge_preview_payload)
        _, _, curves, _ = self.visualizer.edge_preview_payload
        self.assertIn("shift +0.5 eV", curves[0][0])

    def test_new_edge_selection_does_not_inherit_a_saved_shift(self):
        self.layout.elemental_input["chemical_shift"].value = 1.0
        self.layout.elemental_input["soften_edge"].value = False
        self.layout.elemental_input["soften_strength"].value = 2.25
        saved = self.controller.workspace.areas["default"].continuum_specs[0]
        self.assertEqual(saved.chemical_shift.value, 1.0)
        self.assertFalse(saved.broadening.enabled)
        self.assertEqual(saved.broadening.sigma_eV, 2.25)

        self.layout.elemental_input["element_atomic_number"].value = 2

        self.assertEqual(
            self.layout.elemental_input["chemical_shift"].value,
            0.0,
        )
        saved = self.controller.workspace.areas["default"].continuum_specs[0]
        self.assertEqual(saved.chemical_shift.value, 1.0)
        self.assertFalse(saved.broadening.enabled)
        self.assertEqual(saved.broadening.sigma_eV, 2.25)
        self.assertTrue(self.layout.elemental_input["soften_edge"].value)
        self.assertEqual(
            self.layout.elemental_input["soften_strength"].value,
            1.5,
        )
        _, _, curves, _ = self.visualizer.edge_preview_payload
        self.assertIn("He K1 OOS", curves[-1][0])
        self.assertIn("shift +0 eV", curves[-1][0])

    def test_softening_preview_updates_the_saved_definition(self):
        self.assertTrue(self.controller.workspace.is_area_built("default"))
        update_count = len(self.visualizer.edge_preview_updates)

        self.layout.elemental_input["soften_strength"].value = 2.25

        continuum = self.controller.workspace.areas["default"].continuum_specs[0]
        self.assertEqual(continuum.broadening.sigma_eV, 2.25)
        self.assertFalse(self.controller.workspace.is_area_built("default"))
        self.assertGreater(len(self.visualizer.edge_preview_updates), update_count)

    def test_fit_builds_the_dirty_model_automatically(self):
        self.layout.elemental_input["soften_strength"].value = 2.25
        self.assertFalse(self.controller.workspace.is_area_built("default"))
        self.assertFalse(self.layout.elemental_fit_button.disabled)

        self.controller._on_fit(None)

        self.assertTrue(self.controller.workspace.is_area_built("default"))
        self.assertIn("default", self.controller.workspace.reference_fits)

    def test_fit_current_uses_committed_roi_as_default_reference(self):
        self.assertFalse(self.layout.elemental_fit_button.disabled)
        self.assertFalse(self.layout.elemental_fit_area_settings_button.disabled)
        self.assertEqual(
            set(self.layout.elemental_fit_areas_input.options.values()),
            {"cluster_0", "cluster_1"},
        )
        self.controller._on_fit(None)
        snapshot = self.controller.workspace.reference_fits["default"]
        self.assertEqual(snapshot.reference_strategy, "roi_mean")
        self.assertEqual(snapshot.reference_pixel_count, 2)
        self.assertAlmostEqual(self._amplitude(snapshot), 2.0, places=5)
        self.assertTrue(self.controller._reference_is_current("default"))
        results = self.layout.elemental_results_view
        self.assertEqual(self.layout.fitting_tabs.active, 2)
        self.assertEqual(results.area_select.value, "default")
        self.assertEqual(set(results.area_select.options.values()), {"default"})
        self.assertFalse(results.plot_pane.visible)
        self.assertFalse(results.residual_pane.visible)
        self.assertIsInstance(results.plot_pane.object, hv.Overlay)
        self.assertIsInstance(results.residual_pane.object, hv.Overlay)
        self.assertIs(self.visualizer.main_result_plot, results.plot_pane.object)
        self.assertEqual(
            results.layer_selector.options,
            ["Reference", "Best fit", "Components", "Residual"],
        )
        residual_curve = results.plot_pane.object.get(("Curve", "Residual"))
        self.assertIsNotNone(residual_curve)
        results.layer_selector.value = ["Residual"]
        self.assertIs(self.visualizer.main_result_plot, results.plot_pane.object)
        self.assertIsNotNone(results.plot_pane.object.get(("Curve", "Residual")))
        results.layer_selector.value = ["Reference", "Best fit", "Components", "Residual"]
        self.assertIn("Reduced χ²", results.summary_pane.object)
        self.assertIn("Current ROI mean", results.summary_pane.object)
        self.assertFalse(hasattr(results, "parameter_pane"))

        self.visualizer._region_pairs = [(0, 1), (0, 2)]
        self.controller.on_roi_changed()
        self.assertNotIn("default", self.controller.workspace.reference_fits)
        self.assertTrue(self.controller.workspace.is_area_built("default"))
        self.assertEqual(results.area_select.options, {})
        self.assertFalse(results.plot_pane.visible)

    def test_roi_mode_uses_automatic_full_energy_range(self):
        self.assertNotIn("fit_range", self.layout.elemental_input)
        self.assertNotIn("active_area", self.layout.elemental_input)
        self.assertNotIn("default_reference_strategy", self.layout.elemental_input)
        self.assertEqual(
            set(self.layout.elemental_fit_areas_input.options.values()),
            {"cluster_0", "cluster_1"},
        )
        self.controller._on_fit(None)
        snapshot = self.controller.workspace.reference_fits["default"]
        self.assertEqual(snapshot.reference_strategy, "roi_mean")
        self.assertEqual(snapshot.fit_range.minimum, float(np.min(self.eloss)))
        self.assertEqual(snapshot.fit_range.maximum, float(np.max(self.eloss)))

    def test_run_elemental_nlls_commits_dense_result_and_updates_progress(self):
        self.controller._on_fit(None)
        self.assertFalse(self.layout.elemental_run_nlls_button.disabled)

        self.controller._on_run_elemental_nlls(None)
        self.assertEqual(self.state.nlls_run_state, "running")
        self.assertTrue(self.layout.elemental_run_progress.visible)
        self.assertFalse(self.layout.elemental_cancel_button.disabled)
        thread = self.controller._run_thread
        self.assertIsNotNone(thread)
        thread.join(timeout=10.0)
        self.assertFalse(thread.is_alive())
        self.controller._drain_run_events()

        result = self.state.nlls_results
        self.assertIsInstance(result, xr.Dataset)
        self.assertEqual(len(self.published_multifit_results), 1)
        self.assertIs(self.published_multifit_results[0], result)
        self.assertEqual(self.state.nlls_run_state, "complete")
        self.assertEqual(result.attrs["complete"], 1)
        self.assertEqual(result.attrs["cancelled"], 0)
        self.assertEqual(result["BestFit"].dims, ("y", "x", "Eloss"))
        amplitude_name = next(
            name
            for name in result.data_vars
            if name.endswith("_A") and not name.endswith("__stderr")
        )
        np.testing.assert_allclose(
            result[amplitude_name],
            np.where(self.labels == 0, 2.0, 4.0),
            rtol=1e-5,
        )
        self.assertEqual(self.layout.elemental_run_progress.value, 100)
        self.assertFalse(self.layout.elemental_run_progress.active)
        self.assertTrue(self.layout.elemental_cancel_button.disabled)
        self.assertFalse(self.layout.elemental_run_nlls_button.disabled)

    def test_parallel_selector_freezes_workers_and_commits_parallel_result(self):
        self.controller._on_fit(None)
        execution = self.layout.elemental_input["execution_mode"]
        workers = self.layout.elemental_input["workers"]
        self.assertFalse(execution.value)
        self.assertTrue(workers.disabled)
        execution.value = True
        workers.value = min(2, int(workers.end))
        self.controller.multifit_service.parallel_chunk_size = 1
        self.assertFalse(workers.disabled)

        request, *_ = self.controller._freeze_run_inputs()
        self.assertTrue(request.parallel)
        self.assertEqual(request.workers, workers.value)
        self.controller._on_run_elemental_nlls(None)
        thread = self.controller._run_thread
        thread.join(timeout=30.0)
        self.assertFalse(thread.is_alive())
        self.controller._drain_run_events()
        result = self.state.nlls_results
        self.assertEqual(result.attrs["execution_mode"], "parallel")
        self.assertEqual(result.attrs["workers"], workers.value)
        self.assertFalse(workers.disabled)

    def test_center_and_white_line_callbacks_publish_additive_derived_datasets(self):
        result = _dense_nlls_result()
        eloss = np.asarray(result.coords["Eloss"].values, dtype=float)
        shape_a = np.exp(-0.5 * ((eloss - 1.0) / 1.0) ** 2)
        shape_b = np.exp(-0.5 * ((eloss - 3.0) / 1.0) ** 2)
        spatial = result["FitStatus"].shape
        result["a_elnes_center"] = (("y", "x"), np.full(spatial, 1.0))
        result["b_elnes_center"] = (("y", "x"), np.full(spatial, 3.0))
        result["a_elnes__component"] = (
            ("y", "x", "Eloss"),
            np.broadcast_to(shape_a, (*spatial, eloss.size)).copy(),
        )
        result["b_elnes__component"] = (
            ("y", "x", "Eloss"),
            np.broadcast_to(shape_b, (*spatial, eloss.size)).copy(),
        )
        failed = result["FitStatus"].values != int(FitStatus.SUCCESS)
        result["a_elnes__component"].values[failed, :] = np.nan
        result["b_elnes__component"].values[failed, :] = np.nan

        controls = self.layout.elemental_multifit_controls
        run_view = NLLSMultifitResultsPlot(result, run_number=1)
        controls.register(run_view)
        try:
            controls._open_derived_analyses(None)
            self.assertTrue(controls.derived_analyses_modal.visible)
            self.controller._on_compute_center_analysis(None)
            self.assertFalse(controls.derived_analyses_modal.visible)
            controls._open_derived_analyses(None)
            self.assertTrue(controls.derived_analyses_modal.visible)
            self.controller._on_compute_white_lines(None)
            self.assertFalse(controls.derived_analyses_modal.visible)
            self.assertEqual(len(self.published_derived_results), 2)
            center, white_lines = self.published_derived_results
            self.assertEqual(center.attrs["analysis_type"], "center_distance")
            np.testing.assert_allclose(
                center["Distances"].values[0, :2], [2.0, 2.0]
            )
            self.assertEqual(white_lines.attrs["analysis_type"], "white_lines")
            self.assertEqual(
                white_lines.attrs["integration"], "scipy.integrate.simpson"
            )
            self.assertTrue(np.isfinite(white_lines["Ratio"].values[0, 0]))
        finally:
            controls.clear_runs()
            run_view.cleanup()

    def test_consecutive_runs_commit_as_independent_additive_results(self):
        self.controller._on_fit(None)
        self.controller._on_run_elemental_nlls(None)
        thread = self.controller._run_thread
        thread.join(timeout=10.0)
        self.controller._drain_run_events()
        parent = self.state.nlls_results

        self.assertFalse(self.layout.elemental_run_nlls_button.disabled)
        self.controller._on_run_elemental_nlls(None)
        thread = self.controller._run_thread
        thread.join(timeout=10.0)
        self.assertFalse(thread.is_alive())
        self.controller._drain_run_events()

        second = self.state.nlls_results
        self.assertIsNot(second, parent)
        self.assertNotEqual(second.attrs["run_id"], parent.attrs["run_id"])
        self.assertEqual(len(self.published_multifit_results), 2)
        self.assertIs(self.published_multifit_results[-1], second)
        for removed_attr in (
            "modified_areas",
            "parent_run_id",
            "run_kind",
            "run_version",
        ):
            self.assertNotIn(removed_attr, second.attrs)

    def test_run_uses_selected_cluster_areas_only(self):
        self.controller._on_fit(None)
        self.controller._on_use_current_clustering(None)
        self.controller._on_fit(None)
        self.layout.elemental_fit_areas_input.value = ["cluster_1"]
        self.assertFalse(self.layout.elemental_run_nlls_button.disabled)

        self.controller._on_run_elemental_nlls(None)
        thread = self.controller._run_thread
        thread.join(timeout=10.0)
        self.assertFalse(thread.is_alive())
        self.controller._drain_run_events()
        result = self.state.nlls_results
        np.testing.assert_array_equal(
            result["FitStatus"].values[self.labels == 0],
            np.full(4, int(FitStatus.NOT_SELECTED)),
        )
        np.testing.assert_array_equal(
            result["FitStatus"].values[self.labels == 1],
            np.full(2, int(FitStatus.SUCCESS)),
        )

    def test_cancelled_run_preserves_previous_complete_result(self):
        self.controller._on_fit(None)
        self.controller._on_run_elemental_nlls(None)
        thread = self.controller._run_thread
        thread.join(timeout=10.0)
        self.controller._drain_run_events()
        previous = self.state.nlls_results

        request, *_ = self.controller._freeze_run_inputs()
        partial = previous.copy(deep=True)
        partial.attrs.update(complete=0, cancelled=1, processed_pixels=1)
        self.controller._active_run_request = request
        self.controller._run_cancel_event = Event()
        self.controller._run_cancel_event.set()
        self.controller._prior_complete_results = previous
        self.state.nlls_run_state = "cancelling"
        self.controller._commit_run_result(request, partial)

        self.assertIs(self.state.nlls_results, previous)
        self.assertEqual(self.state.nlls_run_state, "idle")
        self.assertIn("cancelled", self.layout.elemental_run_progress.name.lower())

    def test_stale_worker_result_cannot_replace_previous_complete_result(self):
        self.controller._on_fit(None)
        self.controller._on_run_elemental_nlls(None)
        thread = self.controller._run_thread
        thread.join(timeout=10.0)
        self.controller._drain_run_events()
        previous = self.state.nlls_results

        request, *_ = self.controller._freeze_run_inputs()
        stale_result = previous.copy(deep=True)
        self.controller._active_run_request = request
        self.controller._run_cancel_event = Event()
        self.controller._prior_complete_results = previous
        self.controller.workspace.dirty_revision += 1
        self.state.nlls_run_state = "running"
        self.controller._commit_run_result(request, stale_result)

        self.assertIs(self.state.nlls_results, previous)
        self.assertEqual(self.state.nlls_run_state, "error")
        self.assertIn("discarded", self.layout.elemental_run_progress.name.lower())

    def test_clustering_settings_are_disabled_without_a_compatible_result(self):
        self.state.last_clustering_result = None
        self.assertTrue(
            self.layout.elemental_use_current_clustering_button.disabled
        )
        self.assertTrue(self.layout.elemental_fit_area_settings_button.disabled)
        self.assertEqual(self.layout.elemental_fit_areas_input.options, {})

    def test_fit_all_fits_every_cluster_and_isolates_a_failed_cluster(self):
        self.controller._on_fit(None)
        self.controller._on_use_current_clustering(None)
        self.assertEqual(
            self.controller.workspace.runnable_area_ids,
            ("cluster_0", "cluster_1"),
        )
        clustering_labels, clustering_energy, clustering_spectra = (
            self.visualizer.clustering_payload
        )
        np.testing.assert_array_equal(clustering_labels, self.labels)
        np.testing.assert_allclose(clustering_energy, self.eloss)
        self.assertEqual(len(clustering_spectra), 2)
        self.assertEqual(
            self.layout.elemental_fit_areas_input.value,
            ["cluster_0", "cluster_1"],
        )
        self.assertFalse(self.layout.elemental_fit_area_settings_button.disabled)
        self.layout.elemental_fit_areas_input.value = ["cluster_0"]
        self.controller._on_select_all_fit_areas(None)
        self.assertEqual(
            self.layout.elemental_fit_areas_input.value,
            ["cluster_0", "cluster_1"],
        )
        self.assertFalse(self.layout.elemental_fit_button.disabled)
        self.controller._on_fit(None)
        references = self.controller.workspace.reference_fits
        self.assertEqual(
            {"default", "cluster_0", "cluster_1"}, set(references)
        )
        self.assertAlmostEqual(self._amplitude(references["cluster_0"]), 2.0, places=5)
        self.assertAlmostEqual(self._amplitude(references["cluster_1"]), 4.0, places=5)
        results = self.layout.elemental_results_view
        self.assertEqual(self.layout.fitting_tabs.active, 2)
        self.assertEqual(results.area_select.value, "cluster_0")
        self.assertEqual(
            set(results.area_select.options.values()),
            {"default", "cluster_0", "cluster_1"},
        )

        self.dataset["ElectronCount"].values[self.labels == 1, :] = np.nan
        self.controller._on_fit(None)
        references = self.controller.workspace.reference_fits
        self.assertIn("cluster_0", references)
        self.assertNotIn("cluster_1", references)
        self.assertEqual(self.state.nlls_run_state, "error")
        self.assertEqual(
            set(results.area_select.options.values()), {"default", "cluster_0"}
        )

        self.controller._on_use_current_clustering(None)
        self.assertEqual(self.controller.workspace.runnable_area_ids, ("default",))
        self.assertEqual(
            self.layout.elemental_use_current_clustering_button.name,
            "Use Current Clustering",
        )
        self.assertFalse(self.layout.elemental_fit_area_settings_button.disabled)
        self.assertEqual(
            set(self.layout.elemental_fit_areas_input.options.values()),
            {"cluster_0", "cluster_1"},
        )
        self.assertIsNone(self.visualizer.clustering_payload)

    def _assert_sections_locked(self):
        for section in (
            self.layout.elemental_edge_section,
            self.layout.elemental_model_section,
            self.layout.elemental_continuum_section,
            self.layout.elemental_elnes_section,
        ):
            self.assertTrue(section.locked)
            self.assertFalse(section.expanded)
            section.toggle()
            self.assertFalse(section.expanded)

    def test_elemental_sections_are_gated_by_background_and_geometry(self):
        edge = self.layout.elemental_edge_section
        model = self.layout.elemental_model_section
        continuum = self.layout.elemental_continuum_section
        elnes = self.layout.elemental_elnes_section
        background = self.layout.elemental_background_status
        geometry = self.layout.elemental_geometry_status

        # Both gates valid: no alert is published and both sections are open on top.
        self.assertFalse(background.visible)
        self.assertFalse(geometry.visible)
        for section in (edge, model, continuum, elnes):
            self.assertFalse(section.locked)
            self.assertTrue(section.expanded)

        # A section folded by hand stays folded across a refresh of the same source.
        model.toggle()
        self.assertFalse(model.expanded)
        self.controller.on_source_changed()
        self.assertFalse(model.expanded)
        self.assertFalse(model.locked)

        # Geometry alone blocked: only its own alert returns, both sections lock.
        # Editing it in the Dataset Information card republishes all_datasets, which is
        # the only signal the controller gets, so drive the gate through that path.
        self.dataset.attrs["beam_energy"] = 0.0
        self.state.all_datasets = [self.dataset]
        self.assertFalse(background.visible)
        self.assertTrue(geometry.visible)
        self.assertIn("blocked", geometry.object)
        self._assert_sections_locked()

        # Recovering the geometry reopens both sections without touching the alerts.
        self.dataset.attrs["beam_energy"] = 200.0
        self.state.all_datasets = [self.dataset]
        self.assertFalse(background.visible)
        self.assertFalse(geometry.visible)
        for section in (edge, model):
            self.assertFalse(section.locked)
            self.assertTrue(section.expanded)

        # Background provenance missing: its alert returns and locks the sections again.
        raw = xr.Dataset(
            {"ElectronCount": (("y", "x", "Eloss"), np.zeros((2, 3, self.eloss.size)))},
            coords={"y": np.arange(2), "x": np.arange(3), "Eloss": self.eloss},
            attrs={
                "original_name": "synthetic.dm4",
                "image_name": "synthetic",
                "beam_energy": 200.0,
                "collection_angle": 20.0,
                "convergence_angle": 0.0,
            },
        )
        self.state.preprocessed_plot_dataset = None
        self.state.plot_dataset = raw
        self.controller.on_source_changed()
        self.assertTrue(background.visible)
        self.assertIn("blocked", background.object)
        self._assert_sections_locked()

    def test_model_setup_remains_shared_when_clustering_is_enabled_first(self):
        workspace = self.controller.workspace
        workspace.reset_area("default")
        workspace.set_model_composition("default", "continuum_only")
        self.controller._publish_workspace()
        self.controller._refresh_button_states()

        self.controller._on_use_current_clustering(None)
        self.assertTrue(workspace.clustering_active)
        self.assertFalse(
            any(
                workspace.is_area_built(area_id)
                for area_id in workspace.runnable_area_ids
            )
        )

        self.controller._on_add_edge(None)
        self.assertTrue(workspace.areas["default"].continuum_specs)
        self.assertTrue(
            all(workspace.areas[area_id].continuum_specs for area_id in workspace.runnable_area_ids)
        )

        self.controller._on_build_model(None)
        self.assertTrue(workspace.is_area_built("default"))
        self.assertTrue(
            all(workspace.is_area_built(area_id) for area_id in workspace.runnable_area_ids)
        )
        self.assertFalse(self.layout.elemental_fit_button.disabled)


if __name__ == "__main__":
    unittest.main()
