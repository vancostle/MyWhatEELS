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
from types import SimpleNamespace

import numpy as np
import panel as pn
import xarray as xr
from bokeh.models import Tooltip
from whateels.components import SimpleDetails
from whateels.nlls.cross_sections import OOSCurveSnapshot
from whateels.nlls.defaults import OOS_FORMULA_VERSION, OOS_PROVIDER_VERSION, OOS_UNITS
from whateels.nlls.provenance import publish_power_law_subtracted_dataset
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
        self.assertGreaterEqual(len(tooltips), 7)
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
        self.assertNotIn("OOS Status", {detail._title for detail in details})
        static_names = {
            str(widget.name) for widget in layout.select(pn.widgets.StaticText)
        }
        self.assertNotIn("OOS method / version", static_names)
        markdown = "\n".join(
            str(pane.object) for pane in layout.select(pn.pane.Markdown)
        )
        self.assertNotIn("**OOS status:**", markdown)
        self.assertNotIn("Load Clustering JSON", markdown)


class ElementalReferenceControllerTests(unittest.TestCase):
    class FakeProvider:
        @staticmethod
        def available_edges(atomic_number):
            return ("K1",)

        @staticmethod
        def element_info(atomic_number):
            return "Hydrogen", "H"

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
            return OOSCurveSnapshot(
                energy_eV=energy,
                normalized_shape=shape,
                physical_shape=shape,
                normalization_factor=1.0,
                units=OOS_UNITS,
                formula_version=OOS_FORMULA_VERSION,
                provider_version=OOS_PROVIDER_VERSION,
                atomic_number=int(atomic_number),
                symbol="H",
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
        self.visualizer = SimpleNamespace(_region_pairs=[(0, 0), (1, 0)])
        parent = SimpleNamespace(
            layout=SimpleNamespace(_chosen_visualizers=[self.visualizer])
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

    def test_fit_current_uses_committed_roi_as_default_reference(self):
        self.assertFalse(self.layout.elemental_fit_current_reference_button.disabled)
        self.controller._on_fit_current_reference(None)
        snapshot = self.controller.workspace.reference_fits["default"]
        self.assertEqual(snapshot.reference_strategy, "roi_mean")
        self.assertEqual(snapshot.reference_pixel_count, 2)
        self.assertAlmostEqual(self._amplitude(snapshot), 2.0, places=5)
        self.assertTrue(self.controller._reference_is_current("default"))

        self.visualizer._region_pairs = [(0, 1), (0, 2)]
        self.controller.on_roi_changed()
        self.assertNotIn("default", self.controller.workspace.reference_fits)
        self.assertTrue(self.controller.workspace.is_area_built("default"))

    def test_central_reference_option_and_reset_area(self):
        self.layout.elemental_input["default_reference_strategy"].value = "central_mean"
        self.visualizer._region_pairs = []
        self.assertFalse(self.layout.elemental_fit_current_reference_button.disabled)
        self.controller._on_fit_current_reference(None)
        snapshot = self.controller.workspace.reference_fits["default"]
        self.assertEqual(snapshot.reference_strategy, "central_mean")
        self.assertGreater(snapshot.reference_pixel_count, 0)

        self.controller._on_reset_area_model(None)
        workspace = self.controller.workspace
        self.assertEqual(workspace.areas["default"].edges, ())
        self.assertNotIn("default", workspace.model_builds)
        self.assertNotIn("default", workspace.reference_fits)
        self.assertTrue(self.layout.elemental_build_model_button.disabled)
        self.assertTrue(self.layout.elemental_fit_current_reference_button.disabled)

    def test_fit_all_fits_every_cluster_and_isolates_a_failed_cluster(self):
        self.controller._on_fit_current_reference(None)
        self.controller._on_use_current_clustering(None)
        self.assertEqual(
            self.controller.workspace.runnable_area_ids,
            ("cluster_0", "cluster_1"),
        )
        self.assertFalse(self.layout.elemental_fit_all_references_button.disabled)
        self.controller._on_fit_all_references(None)
        references = self.controller.workspace.reference_fits
        self.assertEqual(
            {"default", "cluster_0", "cluster_1"}, set(references)
        )
        self.assertAlmostEqual(self._amplitude(references["cluster_0"]), 2.0, places=5)
        self.assertAlmostEqual(self._amplitude(references["cluster_1"]), 4.0, places=5)

        self.dataset["ElectronCount"].values[self.labels == 1, :] = np.nan
        self.controller._on_fit_all_references(None)
        references = self.controller.workspace.reference_fits
        self.assertIn("cluster_0", references)
        self.assertNotIn("cluster_1", references)
        self.assertEqual(self.state.nlls_run_state, "error")


if __name__ == "__main__":
    unittest.main()
