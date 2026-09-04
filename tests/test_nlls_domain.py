from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from threading import Event

import numpy as np
import xarray as xr

from whateels.nlls.areas import ClusteringAreaAdapter
from whateels.nlls.analysis import (
    CenterAnalysisService,
    WhiteLineRequest,
    WhiteLineService,
)
from whateels.nlls.contracts import (
    AreaModelSpec,
    BroadeningSpec,
    ContinuumSpec,
    DatasetIdentity,
    EdgeSpec,
    ExperimentalGeometry,
    FineStructureSpec,
    FitRange,
    ModelComposition,
    NLLSRunRequest,
)
from whateels.nlls.cross_sections import (
    OOSContinuumProvider,
    OOSCurveSnapshot,
    OOSPhysicalCurve,
)
from whateels.nlls.defaults import (
    CHEMICAL_SHIFT_CONVENTION,
    OOS_FORMULA_VERSION,
    OOS_PROVIDER_VERSION,
    OOS_UNITS,
    canonical_subshell_groups,
    continuum_parameter_specs,
    fine_structure_parameter_specs,
)
from whateels.nlls.errors import (
    InvalidClusteringError,
    InvalidOOSDataError,
    InvalidRunRequestError,
    InvalidSourceError,
    MissingOOSTableError,
)
from whateels.nlls.model_builder import NLLSModelBuilder
from whateels.nlls.multifit import ElementalMultifitService
from whateels.nlls.provenance import (
    publish_power_law_subtracted_dataset,
    validate_background_subtracted,
)
from whateels.nlls.workspace import NLLSWorkspace
from whateels.nlls.references import (
    ReferenceFitService,
    ReferenceSpectrumSelection,
    ReferenceSpectrumService,
)
from whateels.nlls.results import FitStatus


def _write_table(directory: Path, atomic_number: int = 10) -> None:
    payload = [
        "Testium",
        "Ts",
        float(atomic_number),
        {
            "L2": {
                "onset": 100.0,
                "eaxis": [100.0, 105.0, 112.0, 125.0, 145.0],
                "counts": [0.2, 0.19, 0.16, 0.1, 0.04],
            },
            "L3": {
                "onset": 95.0,
                "eaxis": [95.0, 101.0, 110.0, 127.0, 145.0],
                "counts": [0.3, 0.27, 0.2, 0.09, 0.03],
            },
        },
    ]
    (directory / f"OOS{atomic_number:02d}.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def _dataset() -> xr.Dataset:
    eloss = np.linspace(90.0, 145.0, 56)
    counts = np.ones((3, 4, eloss.size), dtype=float)
    return xr.Dataset(
        {"ElectronCount": (("y", "x", "Eloss"), counts)},
        coords={"y": np.arange(3), "x": np.arange(4), "Eloss": eloss},
        attrs={
            "original_name": "synthetic.dm4",
            "image_name": "synthetic",
            "beam_energy": 200.0,
            "collection_angle": 20.0,
            "convergence_angle": 0.0,
        },
    )


def _identity(dataset: xr.Dataset) -> DatasetIdentity:
    published = publish_power_law_subtracted_dataset(
        dataset, dataset["ElectronCount"], fit_range_eV=(90.0, 99.0)
    )
    history = validate_background_subtracted(published)
    return DatasetIdentity.from_dataset(
        published,
        tab_index=0,
        source_kind="preprocessed",
        preprocessing_history=history,
        background_subtracted=True,
    )


def _clustering_result(labels, *, file="synthetic.dm4", image="synthetic"):
    return {
        "clustering": {
            "file": file,
            "spectrum_image": image,
            "type": "K-Means",
            "inputs": {"n_clusters": len(np.unique(labels))},
            "outputs": {"labels": labels, "centres": [[999.0]]},
        }
    }


class NLLSWorkspaceEdgeTests(unittest.TestCase):
    def test_default_chemical_shift_bounds_are_twenty_ev(self):
        _amplitude, chemical_shift = continuum_parameter_specs()

        self.assertEqual(chemical_shift.minimum, -20.0)
        self.assertEqual(chemical_shift.maximum, 20.0)

    @staticmethod
    def _workspace_with_edge():
        dataset = _dataset()
        workspace = NLLSWorkspace.create(
            _identity(dataset), ExperimentalGeometry(200.0, 20.0, 0.0)
        )
        edge = EdgeSpec(
            id="ts_l23_edge",
            atomic_number=10,
            symbol="Ts",
            shells=("L2", "L3"),
            onset_eV=95.0,
        )
        continuum = ContinuumSpec(
            id="ts_l23_continuum",
            edge_id=edge.id,
            atomic_number=10,
            symbol=edge.symbol,
            shells=edge.shells,
            prefix="ts_l23_cont_",
            onset_eV=edge.onset_eV,
            broadening=BroadeningSpec(enabled=True, sigma_eV=1.5),
            amplitude=continuum_parameter_specs(0.0)[0],
            chemical_shift=continuum_parameter_specs(0.5)[1],
            provider_version=OOS_PROVIDER_VERSION,
            chemical_shift_convention=CHEMICAL_SHIFT_CONVENTION,
        )
        center, sigma, amplitude = fine_structure_parameter_specs(95.0, 4.8)
        fine = FineStructureSpec(
            id="ts_l2_elnes",
            edge_id=edge.id,
            shell="L2",
            prefix="ts_l2_elnes_",
            shape="GaussianModel",
            center=center,
            sigma=sigma,
            amplitude=amplitude,
            enabled=True,
        )
        workspace.add_edge("default", edge, continuum, (fine,))
        return workspace, edge, continuum, fine

    def test_remove_edge_deletes_edge_and_its_saved_parts(self):
        workspace, edge, continuum, fine = self._workspace_with_edge()

        updated = workspace.remove_edge("default", edge.id)

        self.assertEqual(updated.edges, ())
        self.assertEqual(updated.continuum_specs, ())
        self.assertEqual(updated.fine_structure_specs, ())
        self.assertFalse(any(item.id == edge.id for item in workspace.areas["default"].edges))

    def test_advanced_parameter_updates_are_typed_and_invalidate_the_area(self):
        workspace, _edge, continuum, fine = self._workspace_with_edge()
        initial_revision = workspace.areas["default"].revision

        updated_amplitude = replace(
            continuum.amplitude,
            value=3.0,
            maximum=8.0,
            vary=False,
        )
        workspace.set_continuum_parameter(
            "default", continuum.id, "amplitude", updated_amplitude
        )
        updated_center = replace(fine.center, value=97.0)
        workspace.set_fine_structure_parameter(
            "default", fine.id, "center", updated_center
        )
        workspace.configure_fine_structure(
            "default", fine.id, shape="LorentzianModel", enabled=False
        )

        area = workspace.areas["default"]
        self.assertEqual(area.continuum_specs[0].amplitude, updated_amplitude)
        self.assertEqual(area.fine_structure_specs[0].center, updated_center)
        self.assertEqual(area.fine_structure_specs[0].shape, "LorentzianModel")
        self.assertFalse(area.fine_structure_specs[0].enabled)
        self.assertEqual(area.revision, initial_revision + 3)
        self.assertFalse(area.is_built)
        with self.assertRaises(ValueError):
            workspace.configure_fine_structure(
                "default", fine.id, shape="UnsupportedModel"
            )

    def test_chemical_shift_translates_associated_elnes_center_and_bounds(self):
        workspace, _edge, continuum, fine = self._workspace_with_edge()

        workspace.set_continuum_chemical_shift(
            "default", (continuum.id,), 2.0
        )
        area = workspace.areas["default"]
        shifted = area.fine_structure_specs[0].center
        self.assertEqual(shifted.value, fine.center.value - 1.5)
        self.assertEqual(shifted.minimum, fine.center.minimum - 1.5)
        self.assertEqual(shifted.maximum, fine.center.maximum - 1.5)

        current_continuum = area.continuum_specs[0]
        workspace.set_continuum_parameter(
            "default",
            current_continuum.id,
            "chemical_shift",
            replace(current_continuum.chemical_shift, value=-1.0),
        )
        restored_direction = workspace.areas["default"].fine_structure_specs[0].center
        self.assertEqual(restored_direction.value, fine.center.value + 1.5)
        self.assertEqual(restored_direction.minimum, fine.center.minimum + 1.5)
        self.assertEqual(restored_direction.maximum, fine.center.maximum + 1.5)


class OOSProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name)
        _write_table(self.data_dir)
        self.provider = OOSContinuumProvider(self.data_dir)
        self.geometry = ExperimentalGeometry(200.0, 20.0, 0.0)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_catalog_load_and_missing_shell(self):
        self.assertEqual(self.provider.available_edges(10), ("L2", "L3"))
        raw = self.provider.load_raw(10, "L2")
        self.assertEqual(raw.symbol, "Ts")
        self.assertEqual(raw.onset_eV, 100.0)
        self.assertTrue(np.all(np.diff(raw.energy_eV) > 0.0))
        with self.assertRaises(MissingOOSTableError):
            self.provider.load_raw(10, "K1")

    def test_cross_section_uses_real_energy_axis(self):
        physical = self.provider.differential_cross_section(
            self.provider.load_raw(10, "L2"), self.geometry
        )
        self.assertEqual(physical.sigma.shape, physical.energy_eV.shape)
        self.assertTrue(np.all(np.isfinite(physical.sigma)))
        self.assertGreater(np.count_nonzero(physical.sigma), 1)
        self.assertGreater(float(np.ptp(physical.sigma)), 0.0)

    def test_finite_alpha_correction_is_finite_and_changes_curve(self):
        raw = self.provider.load_raw(10, "L2")
        parallel = self.provider.differential_cross_section(raw, self.geometry)
        convergent = self.provider.differential_cross_section(
            raw, ExperimentalGeometry(200.0, 20.0, 10.0)
        )
        self.assertTrue(np.all(np.isfinite(convergent.sigma)))
        self.assertGreater(float(np.max(np.abs(convergent.sigma - parallel.sigma))), 0.0)

    def test_doublet_curve_is_normalized_and_reversible(self):
        eloss = np.linspace(90.0, 145.0, 111)
        snapshot = self.provider.curve(
            10,
            ("L2", "L3"),
            self.geometry,
            eloss,
            BroadeningSpec(enabled=False, sigma_eV=0.0),
            FitRange(95.0, 140.0),
        )
        self.assertAlmostEqual(float(np.max(snapshot.normalized_shape)), 1.0)
        np.testing.assert_allclose(
            snapshot.normalized_shape * snapshot.normalization_factor,
            snapshot.physical_shape,
        )
        l2 = self.provider.curve(
            10,
            ("L2",),
            self.geometry,
            eloss,
            BroadeningSpec(enabled=False, sigma_eV=0.0),
            FitRange(95.0, 140.0),
        )
        l3 = self.provider.curve(
            10,
            ("L3",),
            self.geometry,
            eloss,
            BroadeningSpec(enabled=False, sigma_eV=0.0),
            FitRange(95.0, 140.0),
        )
        np.testing.assert_allclose(snapshot.physical_shape, l2.physical_shape + l3.physical_shape)

    def test_integration_uses_irregular_energy_axis(self):
        curve = OOSPhysicalCurve(
            energy_eV=np.array([0.0, 0.25, 1.5, 3.0]),
            sigma=np.array([0.0, 2.0, 2.0, 0.0]),
            units=OOS_UNITS,
            formula_version=OOS_FORMULA_VERSION,
            onset_eV=0.0,
            table_checksums=("test",),
        )
        expected = 4.25
        self.assertAlmostEqual(self.provider.integrate(curve, 0.0, 3.0), expected)

    def test_fit_range_without_edge_support_is_rejected(self):
        with self.assertRaises(InvalidOOSDataError):
            self.provider.curve(
                10,
                ("L2",),
                self.geometry,
                np.linspace(10.0, 50.0, 41),
                BroadeningSpec(enabled=False, sigma_eV=0.0),
                FitRange(10.0, 50.0),
            )

    def test_corrupt_json_is_reported_as_invalid_oos_data(self):
        (self.data_dir / "OOS11.json").write_text("{broken", encoding="utf-8")
        with self.assertRaises(InvalidOOSDataError):
            self.provider.available_edges(11)


class ProvenanceAndWorkspaceTests(unittest.TestCase):
    def test_only_public_power_law_history_unlocks_source(self):
        dataset = _dataset()
        with self.assertRaises(InvalidSourceError):
            validate_background_subtracted(dataset)
        published = publish_power_law_subtracted_dataset(
            dataset,
            dataset["ElectronCount"],
            fit_range_eV=(90.0, 99.0),
        )
        history = validate_background_subtracted(published)
        self.assertTrue(published.attrs["background_subtracted"])
        self.assertEqual(history[-1]["operation"], "power_law_background_subtraction")

    def test_source_revision_changes_when_preprocessed_values_change(self):
        dataset = _dataset()
        first = publish_power_law_subtracted_dataset(
            dataset, dataset["ElectronCount"], fit_range_eV=(90.0, 99.0)
        )
        second_counts = dataset["ElectronCount"].copy(data=dataset["ElectronCount"].values * 2.0)
        second = publish_power_law_subtracted_dataset(
            dataset, second_counts, fit_range_eV=(90.0, 99.0)
        )
        first_revision = validate_background_subtracted(first)[-1]["revision"]
        second_revision = validate_background_subtracted(second)[-1]["revision"]
        self.assertNotEqual(first_revision, second_revision)

    def test_workspace_invalidates_only_changed_area(self):
        dataset = publish_power_law_subtracted_dataset(
            _dataset(), _dataset()["ElectronCount"], fit_range_eV=(90.0, 99.0)
        )
        history = validate_background_subtracted(dataset)
        identity = DatasetIdentity.from_dataset(
            dataset,
            tab_index=0,
            source_kind="preprocessed",
            preprocessing_history=history,
            background_subtracted=True,
        )
        workspace = NLLSWorkspace.create(
            identity, ExperimentalGeometry.from_dataset(dataset)
        )
        workspace.clone_area("default", "cluster_0", "Cluster 0")
        cluster_revision = workspace.areas["cluster_0"].revision
        workspace.set_model_composition("default", ModelComposition.CONTINUUM_ONLY)
        self.assertGreater(workspace.areas["default"].revision, 0)
        self.assertEqual(workspace.areas["cluster_0"].revision, cluster_revision)

    def test_doublet_group_completion(self):
        groups = canonical_subshell_groups(("L3",), ("K1", "L2", "L3"))
        self.assertEqual(groups, (("L2", "L3"),))


class ClusteringAreaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = _dataset()
        self.identity = _identity(self.dataset)
        self.labels = np.array(
            [
                [0, 0, 2, 2],
                [0, 0, 2, 2],
                [0, 0, 2, 2],
            ]
        )

    def test_adapter_builds_stable_exclusive_masks(self):
        areas = ClusteringAreaAdapter.from_result(
            _clustering_result(self.labels), self.identity, (3, 4)
        )
        self.assertEqual(tuple(area.area_id for area in areas), ("cluster_0", "cluster_2"))
        self.assertEqual(tuple(area.label_value for area in areas), (0, 2))
        self.assertEqual(int(np.count_nonzero(areas[0].mask)), 6)
        self.assertEqual(int(np.count_nonzero(areas[1].mask)), 6)
        self.assertFalse(areas[0].mask.flags.writeable)
        self.assertNotEqual(areas[0].mask_fingerprint, areas[1].mask_fingerprint)
        np.testing.assert_array_equal(
            areas[0].mask.astype(int) + areas[1].mask.astype(int),
            np.ones((3, 4), dtype=int),
        )

    def test_adapter_rejects_wrong_shape_and_dataset_identity(self):
        with self.assertRaises(InvalidClusteringError):
            ClusteringAreaAdapter.from_result(
                _clustering_result(self.labels), self.identity, (4, 3)
            )
        with self.assertRaises(InvalidClusteringError):
            ClusteringAreaAdapter.from_result(
                _clustering_result(self.labels, file="different.dm4"),
                self.identity,
                (3, 4),
            )

    def test_adapter_rejects_non_integral_or_negative_labels(self):
        invalid = self.labels.astype(float)
        invalid[0, 0] = 0.5
        with self.assertRaises(InvalidClusteringError):
            ClusteringAreaAdapter.from_result(
                _clustering_result(invalid), self.identity, (3, 4)
            )
        invalid[0, 0] = -1.0
        with self.assertRaises(InvalidClusteringError):
            ClusteringAreaAdapter.from_result(
                _clustering_result(invalid), self.identity, (3, 4)
            )

    def test_workspace_applies_independent_cluster_areas_and_preserves_masks_on_reset(self):
        workspace = NLLSWorkspace.create(
            self.identity, ExperimentalGeometry.from_dataset(self.dataset)
        )
        workspace.set_model_composition("default", ModelComposition.CONTINUUM_ONLY)
        definitions = ClusteringAreaAdapter.from_result(
            _clustering_result(self.labels), self.identity, (3, 4)
        )
        clustered = workspace.apply_clustering(definitions)
        self.assertEqual(workspace.runnable_area_ids, ("cluster_0", "cluster_2"))
        self.assertEqual(workspace.active_area, "cluster_0")
        self.assertEqual(
            clustered[0].model_composition, ModelComposition.CONTINUUM_ONLY
        )
        workspace.set_model_composition("cluster_0", ModelComposition.CONTINUUM_PLUS_ELNES)
        self.assertEqual(
            workspace.areas["cluster_2"].model_composition,
            ModelComposition.CONTINUUM_ONLY,
        )

        fingerprint = workspace.areas["cluster_0"].mask_fingerprint
        mask = workspace.areas["cluster_0"].mask.copy()
        workspace.reset_area("cluster_0")
        self.assertEqual(workspace.areas["cluster_0"].mask_fingerprint, fingerprint)
        np.testing.assert_array_equal(workspace.areas["cluster_0"].mask, mask)

        workspace.clear_clustering()
        self.assertFalse(workspace.clustering_active)
        self.assertEqual(workspace.runnable_area_ids, ("default",))
        self.assertEqual(workspace.active_area, "default")
        self.assertEqual(set(workspace.areas), {"default"})

    def test_cluster_reference_is_recomputed_from_active_cube_not_saved_centres(self):
        areas = ClusteringAreaAdapter.from_result(
            _clustering_result(self.labels), self.identity, (3, 4)
        )
        cube = np.arange(3 * 4 * 5, dtype=float).reshape(3, 4, 5)
        reference = ReferenceSpectrumService.from_mask(cube, areas[1].mask)
        np.testing.assert_allclose(reference, np.mean(cube[self.labels == 2], axis=0))
        self.assertFalse(np.any(reference == 999.0))


class BuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = OOSCurveSnapshot(
            energy_eV=np.array([0.0, 1.0, 2.0]),
            normalized_shape=np.array([0.0, 1.0, 0.0]),
            physical_shape=np.array([0.0, 2.0, 0.0]),
            normalization_factor=2.0,
            units=OOS_UNITS,
            formula_version=OOS_FORMULA_VERSION,
            provider_version=OOS_PROVIDER_VERSION,
            atomic_number=10,
            symbol="Ts",
            shells=("L2", "L3"),
            onsets_eV=(1.0, 1.1),
            table_checksums=("a", "b"),
            broadening_sigma_eV=0.0,
            fit_range=FitRange(0.0, 2.0),
        )

        class FakeProvider:
            def curve(inner_self, *args, **kwargs):
                return self.snapshot

        self.builder = NLLSModelBuilder(FakeProvider())
        amp, shift = continuum_parameter_specs()
        center, sigma, fine_amp = fine_structure_parameter_specs(1.0, 1.0)
        self.area = AreaModelSpec(
            area_id="default",
            label="Default",
            edges=(EdgeSpec("ts_l23_edge", 10, "Ts", ("L2", "L3"), 1.0),),
            continuum_specs=(
                ContinuumSpec(
                    id="ts_l23_continuum",
                    edge_id="ts_l23_edge",
                    atomic_number=10,
                    symbol="Ts",
                    shells=("L2", "L3"),
                    prefix="ts_l23_cont_",
                    onset_eV=1.0,
                    broadening=BroadeningSpec(False, 0.0),
                    amplitude=amp,
                    chemical_shift=shift,
                    provider_version=OOS_PROVIDER_VERSION,
                    chemical_shift_convention=CHEMICAL_SHIFT_CONVENTION,
                ),
            ),
            fine_structure_specs=(
                FineStructureSpec(
                    id="ts_l2_elnes",
                    edge_id="ts_l23_edge",
                    shell="L2",
                    prefix="ts_l2_elnes_",
                    shape="GaussianModel",
                    center=center,
                    sigma=sigma,
                    amplitude=fine_amp,
                ),
            ),
        )

    def test_positive_shift_moves_oos_feature_to_lower_energy(self):
        model = self.builder._make_oos_component(self.snapshot, "test_")
        params = model.make_params(A=1.0, chemical_shift=1.0)
        evaluated = model.eval(params=params, x=np.array([0.0, 1.0, 2.0]))
        self.assertEqual(int(np.argmax(evaluated)), 0)

    def test_continuum_only_excludes_elnes_parameters(self):
        area = replace(self.area, model_composition=ModelComposition.CONTINUUM_ONLY)
        built = self.builder.build(
            area, ExperimentalGeometry(200.0, 20.0, 0.0), np.array([0.0, 1.0, 2.0])
        )
        self.assertIn("ts_l23_cont_A", built.params)
        self.assertNotIn("ts_l2_elnes_center", built.params)

    def test_continuum_plus_elnes_includes_both_component_types(self):
        built = self.builder.build(
            self.area,
            ExperimentalGeometry(200.0, 20.0, 0.0),
            np.array([0.0, 1.0, 2.0]),
        )
        self.assertIn("ts_l23_cont_A", built.params)
        self.assertIn("ts_l2_elnes_center", built.params)

    def test_reference_fit_returns_lightweight_snapshot(self):
        area = replace(self.area, model_composition=ModelComposition.CONTINUUM_ONLY)
        geometry = ExperimentalGeometry(200.0, 20.0, 0.0)
        eloss = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
        built = self.builder.build(area, geometry, eloss)
        generating = built.params.copy()
        generating["ts_l23_cont_A"].value = 5.0
        reference = built.model.eval(params=generating, x=eloss)
        dataset = publish_power_law_subtracted_dataset(
            _dataset(), _dataset()["ElectronCount"], fit_range_eV=(90.0, 99.0)
        )
        history = validate_background_subtracted(dataset)
        identity = DatasetIdentity.from_dataset(
            dataset,
            tab_index=0,
            source_kind="preprocessed",
            preprocessing_history=history,
            background_subtracted=True,
        )
        snapshot = ReferenceFitService(self.builder).fit_area(
            area,
            geometry,
            identity,
            reference,
            eloss,
            FitRange(0.0, 2.0),
        )
        self.assertTrue(snapshot.success)
        fitted = {item["name"]: item["value"] for item in snapshot.params}
        self.assertAlmostEqual(fitted["ts_l23_cont_A"], 5.0, places=6)
        self.assertIsInstance(snapshot.best_fit, np.ndarray)
        self.assertFalse(snapshot.best_fit.flags.writeable)
        self.assertFalse(snapshot.reference_spectrum.flags.writeable)

    def test_model_build_snapshot_contains_portable_preview_and_provenance(self):
        area = replace(self.area, model_composition=ModelComposition.CONTINUUM_ONLY)
        geometry = ExperimentalGeometry(200.0, 20.0, 0.0)
        eloss = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
        built = self.builder.build(area, geometry, eloss, FitRange(0.0, 2.0))
        identity = _identity(_dataset())
        snapshot = self.builder.snapshot(built, area, identity, eloss)
        self.assertEqual(snapshot.area_id, "default")
        self.assertEqual(snapshot.component_ids, ("ts_l23_continuum",))
        self.assertEqual(snapshot.preview.shape, eloss.shape)
        self.assertFalse(snapshot.preview.flags.writeable)
        self.assertEqual(snapshot.dataset_source_revision, identity.source_revision)
        self.assertEqual(snapshot.curve_metadata[0]["provider_version"], OOS_PROVIDER_VERSION)
        workspace = NLLSWorkspace.create(identity, geometry)
        workspace.areas["default"] = area
        workspace.commit_model_build(snapshot)
        self.assertTrue(workspace.is_area_built("default"))
        workspace.reset_area("default")
        self.assertFalse(workspace.is_area_built("default"))
        self.assertNotIn("default", workspace.model_builds)
        self.assertEqual(workspace.areas["default"].edges, ())

    def test_fit_many_isolates_one_invalid_reference(self):
        geometry = ExperimentalGeometry(200.0, 20.0, 0.0)
        eloss = np.array([0.0, 0.5, 1.0, 1.5, 2.0])
        good_area = replace(
            self.area,
            area_id="cluster_0",
            model_composition=ModelComposition.CONTINUUM_ONLY,
        )
        bad_area = replace(good_area, area_id="cluster_1")
        built = self.builder.build(good_area, geometry, eloss)
        generating = built.params.copy()
        generating["ts_l23_cont_A"].value = 4.0
        reference = built.model.eval(params=generating, x=eloss)
        identity = _identity(_dataset())
        batch = ReferenceFitService(self.builder).fit_many(
            (good_area, bad_area),
            geometry,
            identity,
            {
                "cluster_0": ReferenceSpectrumSelection(
                    reference, "clustering_mean", 6, "mask-0"
                ),
                "cluster_1": ReferenceSpectrumSelection(
                    np.array([1.0, 2.0]), "clustering_mean", 6, "mask-1"
                ),
            },
            eloss,
            FitRange(0.0, 2.0),
        )
        self.assertEqual(batch.successful_area_ids, ("cluster_0",))
        self.assertEqual(batch.failed_area_ids, ("cluster_1",))
        self.assertEqual(batch.failures[0].error_type, "InsufficientReferenceDataError")


class DerivedAnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.eloss = np.linspace(0.0, 10.0, 101)
        shape_a = np.exp(-0.5 * ((self.eloss - 3.0) / 0.5) ** 2)
        shape_b = np.exp(-0.5 * ((self.eloss - 7.0) / 0.7) ** 2)
        amplitudes_a = np.array([[2.0, 3.0], [4.0, 5.0]])
        amplitudes_b = np.array([[1.0, 2.0], [3.0, 4.0]])
        component_a = amplitudes_a[..., None] * shape_a
        component_b = amplitudes_b[..., None] * shape_b
        status = np.array(
            [
                [int(FitStatus.SUCCESS), int(FitStatus.SUCCESS)],
                [int(FitStatus.SUCCESS), int(FitStatus.FIT_ERROR)],
            ],
            dtype=np.int8,
        )
        for values in (component_a, component_b):
            values[1, 1, :] = np.nan
        centers_a = np.array([[3.0, 3.1], [3.2, np.nan]])
        centers_b = np.array([[7.0, 7.2], [7.4, np.nan]])
        self.results = xr.Dataset(
            {
                "OriginalData": (
                    ("y", "x", "Eloss"),
                    np.nan_to_num(component_a) + np.nan_to_num(component_b),
                ),
                "AreaLabel": (
                    ("y", "x"),
                    np.array([[0, 0], [1, 1]], dtype=np.int32),
                ),
                "FitStatus": (("y", "x"), status),
                "a_elnes__component": (("y", "x", "Eloss"), component_a),
                "b_elnes__component": (("y", "x", "Eloss"), component_b),
                "a_elnes_center": (("y", "x"), centers_a),
                "a_elnes_center__stderr": (
                    ("y", "x"),
                    np.full((2, 2), 0.1),
                ),
                "b_elnes_center": (("y", "x"), centers_b),
                "b_elnes_center__stderr": (
                    ("y", "x"),
                    np.full((2, 2), 0.1),
                ),
            },
            coords={"y": [0, 1], "x": [0, 1], "Eloss": self.eloss},
            attrs={
                "run_id": "analysis-parent",
                "dataset_source_revision": "analysis-source",
                "geometry": json.dumps(
                    {
                        "beam_energy_keV": 200.0,
                        "collection_angle_mrad": 20.0,
                        "convergence_angle_mrad": 0.0,
                        "provenance": "test",
                    }
                ),
            },
        )

    def test_center_analysis_propagates_fit_status_and_units(self):
        service = CenterAnalysisService()
        self.assertEqual(
            service.available_centers(self.results),
            ("a_elnes_center", "b_elnes_center"),
        )
        derived = service.compute(
            self.results, "a_elnes_center", "b_elnes_center"
        )
        np.testing.assert_allclose(
            derived["Distances"],
            np.array([[4.0, 4.1], [4.2, np.nan]]),
            equal_nan=True,
        )
        self.assertEqual(derived["Distances"].attrs["units"], "eV")
        self.assertEqual(derived.attrs["source_run_id"], "analysis-parent")

    def test_white_lines_use_simpson_for_manual_and_auto_windows(self):
        service = WhiteLineService()
        manual = service.compute(
            self.results,
            WhiteLineRequest(
                component_a="a_elnes",
                component_b="b_elnes",
                window_mode="manual",
                window_a=(2.0, 4.0),
                window_b=(5.5, 8.5),
            ),
        )
        from scipy.integrate import simpson as scipy_simpson

        mask_a = (self.eloss >= 2.0) & (self.eloss <= 4.0)
        expected = scipy_simpson(
            self.results["a_elnes__component"].values[0, 0, mask_a],
            x=self.eloss[mask_a],
        )
        self.assertAlmostEqual(manual["IntensityA"].values[0, 0], expected)
        self.assertTrue(np.isnan(manual["Ratio"].values[1, 1]))
        self.assertEqual(manual.attrs["integration"], "scipy.integrate.simpson")

        automatic = service.compute(
            self.results,
            WhiteLineRequest("a_elnes", "b_elnes", window_mode="auto"),
        )
        self.assertTrue(np.isfinite(automatic["Ratio"].values[0, 0]))
        self.assertGreater(
            automatic["WindowMaxA"].values[0, 0]
            - automatic["WindowMinA"].values[0, 0],
            0.0,
        )

class ElementalMultifitTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = BuilderTests("test_continuum_only_excludes_elnes_parameters")
        fixture.setUp()
        self.builder = fixture.builder
        self.area = replace(
            fixture.area,
            model_composition=ModelComposition.CONTINUUM_ONLY,
            fine_structure_specs=(),
        )
        self.geometry = ExperimentalGeometry(200.0, 20.0, 0.0)
        self.eloss = np.linspace(0.0, 2.0, 17)
        self.fit_range = FitRange(0.0, 2.0)

    def _source(self, amplitudes: np.ndarray, *, invalid=None):
        amplitudes = np.asarray(amplitudes, dtype=float)
        built = self.builder.build(
            self.area, self.geometry, self.eloss, self.fit_range
        )
        unit = built.params.copy()
        unit["ts_l23_cont_A"].value = 1.0
        shape = np.asarray(built.model.eval(params=unit, x=self.eloss), dtype=float)
        cube = amplitudes[..., None] * shape[None, None, :]
        if invalid is not None:
            cube[invalid] = np.nan
        raw = xr.Dataset(
            {"ElectronCount": (("y", "x", "Eloss"), cube)},
            coords={
                "y": np.arange(cube.shape[0]),
                "x": np.arange(cube.shape[1]),
                "Eloss": self.eloss,
            },
            attrs={
                "original_name": "multifit.dm4",
                "image_name": "multifit",
                "beam_energy": 200.0,
                "collection_angle": 20.0,
                "convergence_angle": 0.0,
            },
        )
        source = publish_power_law_subtracted_dataset(
            raw, raw["ElectronCount"], fit_range_eV=(0.0, 0.25)
        )
        history = validate_background_subtracted(source)
        identity = DatasetIdentity.from_dataset(
            source,
            tab_index=0,
            source_kind="preprocessed",
            preprocessing_history=history,
            background_subtracted=True,
        )
        return source, identity, shape

    def _reference(self, area, identity, amplitude):
        built = self.builder.build(area, self.geometry, self.eloss, self.fit_range)
        params = built.params.copy()
        params["ts_l23_cont_A"].value = float(amplitude)
        spectrum = built.model.eval(params=params, x=self.eloss)
        return ReferenceFitService(self.builder).fit_area(
            area,
            self.geometry,
            identity,
            spectrum,
            self.eloss,
            self.fit_range,
        )

    def _request(self, *areas):
        return NLLSRunRequest(
            selected_areas=tuple(area.area_id for area in areas),
            fit_range=self.fit_range,
            method="leastsq",
            model_composition_by_area=tuple(
                (area.area_id, area.model_composition) for area in areas
            ),
            dataset_source_revision=self.identity.source_revision,
            workspace_revision=11,
            area_revisions=tuple(
                (area.area_id, area.revision) for area in areas
            ),
        )

    def test_run_request_rejects_overlap_between_default_and_clusters(self):
        with self.assertRaises(ValueError):
            NLLSRunRequest(
                selected_areas=("default", "cluster_0"),
                fit_range=self.fit_range,
                method="leastsq",
                model_composition_by_area=(
                    ("default", ModelComposition.CONTINUUM_ONLY),
                    ("cluster_0", ModelComposition.CONTINUUM_ONLY),
                ),
            )

    def test_serial_run_produces_dense_numeric_reproducible_dataset(self):
        source, self.identity, _ = self._source(
            np.array([[1.5, 3.0], [5.0, 8.0]])
        )
        reference = self._reference(self.area, self.identity, 3.0)
        request = self._request(self.area)
        service = ElementalMultifitService(self.builder, progress_chunk_size=2)
        first = service.fit_areas(
            request,
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
        )
        second = service.fit_areas(
            request,
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
        )

        required = {
            "OriginalData",
            "AreaLabel",
            "FitStatus",
            "ReducedChiSquare",
            "BestFit",
            "Residuals",
            "ts_l23_continuum__component",
            "ts_l23_cont_A",
            "ts_l23_cont_A__stderr",
        }
        self.assertTrue(required.issubset(first.data_vars))
        self.assertEqual(first["BestFit"].dims, ("y", "x", "Eloss"))
        self.assertTrue(
            all(variable.dtype != object for variable in first.variables.values())
        )
        np.testing.assert_allclose(first["OriginalData"], source["ElectronCount"])
        np.testing.assert_allclose(
            first["ts_l23_cont_A"], np.array([[1.5, 3.0], [5.0, 8.0]]), rtol=1e-5
        )
        np.testing.assert_array_equal(
            first["FitStatus"], np.full((2, 2), int(FitStatus.SUCCESS))
        )
        self.assertEqual(first.attrs["complete"], 1)
        self.assertEqual(first.attrs["cancelled"], 0)
        for name in first.data_vars:
            np.testing.assert_allclose(first[name], second[name], equal_nan=True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "elemental-nlls.nc"
            first.to_netcdf(path)
            restored = xr.load_dataset(path)
            try:
                self.assertEqual(set(restored.data_vars), set(first.data_vars))
                self.assertTrue(
                    all(variable.dtype != object for variable in restored.variables.values())
                )
            finally:
                restored.close()

    def test_parallel_worker_matches_serial_numeric_outputs(self):
        source, self.identity, _ = self._source(
            np.array([[1.5, 3.0], [5.0, 8.0]])
        )
        reference = self._reference(self.area, self.identity, 3.0)
        serial_request = self._request(self.area)
        parallel_request = replace(serial_request, parallel=True, workers=2)
        service = ElementalMultifitService(
            self.builder,
            progress_chunk_size=1,
            parallel_chunk_size=1,
        )
        serial = service.fit_areas(
            serial_request,
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
        )
        parallel = service.fit_areas(
            parallel_request,
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
        )
        self.assertEqual(parallel.attrs["execution_mode"], "parallel")
        self.assertEqual(parallel.attrs["workers"], 2)
        for name in serial.data_vars:
            np.testing.assert_allclose(
                parallel[name], serial[name], rtol=1e-10, atol=1e-12, equal_nan=True
            )

        for removed_attr in (
            "modified_areas",
            "parent_run_id",
            "run_kind",
            "run_version",
        ):
            self.assertNotIn(removed_attr, serial.attrs)
            self.assertNotIn(removed_attr, parallel.attrs)

    def test_every_pixel_receives_an_independent_reference_parameter_copy(self):
        source, self.identity, _ = self._source(np.array([[40.0, 1.25]]))
        reference = self._reference(self.area, self.identity, 4.0)
        request = self._request(self.area)

        class RecordingService(ElementalMultifitService):
            def __init__(inner_self, builder):
                super().__init__(builder, progress_chunk_size=1)
                inner_self.initial_amplitudes = []

            def _fit_pixel(inner_self, built, area, snapshot, *args, **kwargs):
                initial = inner_self._initial_params_for_pixel(built, snapshot)
                inner_self.initial_amplitudes.append(
                    float(initial["ts_l23_cont_A"].value)
                )
                initial["ts_l23_cont_A"].value = 123.0
                return super()._fit_pixel(built, area, snapshot, *args, **kwargs)

        service = RecordingService(self.builder)
        result = service.fit_areas(
            request,
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
        )
        self.assertEqual(len(service.initial_amplitudes), 2)
        np.testing.assert_allclose(service.initial_amplitudes, [4.0, 4.0], rtol=1e-6)
        np.testing.assert_allclose(result["ts_l23_cont_A"], [[40.0, 1.25]], rtol=1e-5)

    def test_each_area_uses_its_own_reference_and_order_is_irrelevant(self):
        source, self.identity, _ = self._source(
            np.array([[2.0, 2.5], [7.0, 7.5]])
        )
        top = np.array([[True, True], [False, False]])
        bottom = ~top
        first_area = replace(
            self.area,
            area_id="cluster_0",
            label="Cluster 0",
            mask=top,
            mask_fingerprint="top",
            clustering_label=0,
            reference_strategy="clustering_mean",
        )
        second_area = replace(
            self.area,
            area_id="cluster_1",
            label="Cluster 1",
            mask=bottom,
            mask_fingerprint="bottom",
            clustering_label=1,
            reference_strategy="clustering_mean",
        )
        references = {
            "cluster_0": self._reference(first_area, self.identity, 2.25),
            "cluster_1": self._reference(second_area, self.identity, 7.25),
        }
        areas = {"cluster_0": first_area, "cluster_1": second_area}
        forward = ElementalMultifitService(self.builder).fit_areas(
            self._request(first_area, second_area),
            source,
            self.geometry,
            self.identity,
            areas,
            references,
        )
        class ReversePixelService(ElementalMultifitService):
            @staticmethod
            def _selected_coordinates(mask):
                return ElementalMultifitService._selected_coordinates(mask)[::-1]

        reverse = ReversePixelService(self.builder).fit_areas(
            self._request(second_area, first_area),
            source,
            self.geometry,
            self.identity,
            areas,
            references,
        )
        np.testing.assert_allclose(
            forward["ts_l23_cont_A"],
            np.array([[2.0, 2.5], [7.0, 7.5]]),
            rtol=1e-5,
        )
        for name in forward.data_vars:
            np.testing.assert_allclose(forward[name], reverse[name], equal_nan=True)

    def test_pixel_error_is_isolated_and_overlapping_masks_fail_before_fit(self):
        source, self.identity, _ = self._source(
            np.array([[2.0, 3.0]]), invalid=(0, 1)
        )
        reference = self._reference(self.area, self.identity, 2.0)
        result = ElementalMultifitService(self.builder).fit_areas(
            self._request(self.area),
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
        )
        np.testing.assert_array_equal(
            result["FitStatus"],
            [[int(FitStatus.SUCCESS), int(FitStatus.INSUFFICIENT_DATA)]],
        )
        self.assertTrue(np.isnan(result["BestFit"].values[0, 1]).all())

        mask = np.array([[True, False]])
        first_area = replace(
            self.area,
            area_id="cluster_0",
            mask=mask,
            clustering_label=0,
        )
        second_area = replace(
            self.area,
            area_id="cluster_1",
            mask=mask.copy(),
            clustering_label=1,
        )
        with self.assertRaises(InvalidRunRequestError):
            ElementalMultifitService(self.builder).fit_areas(
                self._request(first_area, second_area),
                source,
                self.geometry,
                self.identity,
                {"cluster_0": first_area, "cluster_1": second_area},
                {
                    "cluster_0": self._reference(first_area, self.identity, 2.0),
                    "cluster_1": self._reference(second_area, self.identity, 2.0),
                },
            )

    def test_cancellation_marks_pending_pixels_and_returns_incomplete_result(self):
        source, self.identity, _ = self._source(np.array([[1.0, 2.0, 3.0, 4.0]]))
        reference = self._reference(self.area, self.identity, 2.0)
        cancelled = Event()
        progress = []

        def on_progress(done, total):
            progress.append((done, total))
            if done == 1:
                cancelled.set()

        result = ElementalMultifitService(
            self.builder, progress_chunk_size=1
        ).fit_areas(
            self._request(self.area),
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
            cancel_event=cancelled,
            progress_callback=on_progress,
        )
        self.assertEqual(progress[:2], [(0, 4), (1, 4)])
        self.assertEqual(result.attrs["complete"], 0)
        self.assertEqual(result.attrs["cancelled"], 1)
        self.assertEqual(result.attrs["processed_pixels"], 1)
        np.testing.assert_array_equal(
            result["FitStatus"],
            [[
                int(FitStatus.SUCCESS),
                int(FitStatus.CANCELLED),
                int(FitStatus.CANCELLED),
                int(FitStatus.CANCELLED),
            ]],
        )

    def test_parallel_cancellation_stops_submitting_new_chunks(self):
        source, self.identity, _ = self._source(
            np.array([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]])
        )
        reference = self._reference(self.area, self.identity, 2.0)
        request = replace(self._request(self.area), parallel=True, workers=2)
        cancelled = Event()

        def on_progress(done, total):
            if done >= 1:
                cancelled.set()

        result = ElementalMultifitService(
            self.builder,
            progress_chunk_size=1,
            parallel_chunk_size=1,
        ).fit_areas(
            request,
            source,
            self.geometry,
            self.identity,
            {"default": self.area},
            {"default": reference},
            cancel_event=cancelled,
            progress_callback=on_progress,
        )
        self.assertEqual(result.attrs["complete"], 0)
        self.assertEqual(result.attrs["cancelled"], 1)
        self.assertLess(result.attrs["processed_pixels"], 8)
        self.assertGreater(
            int(np.count_nonzero(result["FitStatus"] == int(FitStatus.CANCELLED))),
            0,
        )

if __name__ == "__main__":
    unittest.main()
