"""Mutation-controlled workspace for Elemental NLLS area configuration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, replace

import numpy as np

from .areas import AreaDefinition

from .contracts import (
    AreaModelSpec,
    ContinuumSpec,
    DatasetIdentity,
    EdgeSpec,
    ExperimentalGeometry,
    FineStructureSpec,
    ModelBuildSnapshot,
    ModelComposition,
    ReferenceFitSnapshot,
)
from .defaults import SCHEMA_VERSION


@dataclass
class NLLSWorkspace:
    dataset_identity: DatasetIdentity
    geometry: ExperimentalGeometry
    schema_version: int = SCHEMA_VERSION
    areas: dict[str, AreaModelSpec] = field(default_factory=dict)
    active_area: str = "default"
    reference_fits: dict[str, ReferenceFitSnapshot] = field(default_factory=dict)
    model_builds: dict[str, ModelBuildSnapshot] = field(default_factory=dict)
    dirty_revision: int = 0

    @classmethod
    def create(
        cls,
        dataset_identity: DatasetIdentity,
        geometry: ExperimentalGeometry,
    ) -> "NLLSWorkspace":
        default = AreaModelSpec(area_id="default", label="Default")
        return cls(
            dataset_identity=dataset_identity,
            geometry=geometry,
            areas={"default": default},
        )

    @property
    def active_area_spec(self) -> AreaModelSpec:
        return self.areas[self.active_area]

    @property
    def runnable_area_ids(self) -> tuple[str, ...]:
        clustered = tuple(area_id for area_id in self.areas if area_id != "default")
        return clustered or ("default",)

    @property
    def clustering_active(self) -> bool:
        """Whether the default ROI template is currently expanded into clusters."""
        return any(area_id != "default" for area_id in self.areas)

    def _replace_area(self, area: AreaModelSpec, *, invalidate: bool = True) -> AreaModelSpec:
        if invalidate:
            area = replace(area, revision=area.revision + 1, built_revision=None)
            self.model_builds.pop(area.area_id, None)
            self.reference_fits.pop(area.area_id, None)
        self.areas[area.area_id] = area
        self.dirty_revision += 1
        return area

    def add_edge(
        self,
        area_id: str,
        edge: EdgeSpec,
        continuum: ContinuumSpec,
        fine_structures: tuple[FineStructureSpec, ...],
    ) -> AreaModelSpec:
        area = self.areas[area_id]
        edges = tuple(item for item in area.edges if item.id != edge.id) + (edge,)
        continua = tuple(item for item in area.continuum_specs if item.id != continuum.id) + (
            continuum,
        )
        fine_ids = {item.id for item in fine_structures}
        fine = tuple(item for item in area.fine_structure_specs if item.id not in fine_ids)
        fine += tuple(fine_structures)
        return self._replace_area(
            replace(
                area,
                edges=edges,
                continuum_specs=continua,
                fine_structure_specs=fine,
            )
        )

    def set_model_composition(
        self, area_id: str, composition: ModelComposition | str
    ) -> AreaModelSpec:
        parsed = ModelComposition.parse(composition)
        area = self.areas[area_id]
        if area.model_composition is parsed:
            return area
        return self._replace_area(replace(area, model_composition=parsed))

    def set_reference_strategy(self, area_id: str, strategy: str) -> AreaModelSpec:
        if strategy not in {"roi_mean", "central_mean", "clustering_mean"}:
            raise ValueError(f"unsupported reference strategy: {strategy}")
        area = self.areas[area_id]
        if area.reference_strategy == strategy:
            return area
        updated = replace(area, reference_strategy=strategy)
        self.areas[area_id] = updated
        self.reference_fits.pop(area_id, None)
        self.dirty_revision += 1
        return updated

    def clone_area(self, source_area: str, area_id: str, label: str) -> AreaModelSpec:
        if area_id in self.areas:
            raise ValueError(f"area already exists: {area_id}")
        clone = deepcopy(self.areas[source_area])
        source_built = self.is_area_built(source_area)
        clone = replace(
            clone,
            area_id=area_id,
            label=label,
            revision=0,
            built_revision=0 if source_built else None,
        )
        self.areas[area_id] = clone
        if source_built:
            self.model_builds[area_id] = replace(
                deepcopy(self.model_builds[source_area]),
                area_id=area_id,
                area_revision=0,
            )
        self.dirty_revision += 1
        return clone

    def apply_clustering(
        self,
        definitions: tuple[AreaDefinition, ...],
        template_area: str = "default",
    ) -> tuple[AreaModelSpec, ...]:
        """Replace segmented areas with independent copies of the template model."""
        if not definitions:
            raise ValueError("clustering must contain at least one area")
        template = self.areas[template_area]
        if len({definition.area_id for definition in definitions}) != len(definitions):
            raise ValueError("clustering area identifiers must be unique")

        retained_references = {
            area_id: snapshot
            for area_id, snapshot in self.reference_fits.items()
            if area_id == template_area
        }
        retained_builds = {
            area_id: snapshot
            for area_id, snapshot in self.model_builds.items()
            if area_id == template_area
        }
        template_built = self.is_area_built(template_area)
        clustered: list[AreaModelSpec] = []
        new_areas = {template_area: template}
        for definition in definitions:
            if definition.area_id == template_area:
                raise ValueError("clustering area cannot replace the default template")
            mask = np.array(definition.mask, dtype=bool, copy=True, order="C")
            mask.setflags(write=False)
            clone = replace(
                deepcopy(template),
                area_id=definition.area_id,
                label=definition.label,
                mask=mask,
                mask_fingerprint=definition.mask_fingerprint,
                clustering_label=definition.label_value,
                revision=0,
                built_revision=0 if template_built else None,
                reference_strategy="clustering_mean",
            )
            new_areas[clone.area_id] = clone
            if template_built:
                retained_builds[clone.area_id] = replace(
                    deepcopy(self.model_builds[template_area]),
                    area_id=clone.area_id,
                    area_revision=0,
                )
            clustered.append(clone)

        self.areas = new_areas
        self.reference_fits = retained_references
        self.model_builds = retained_builds
        self.active_area = clustered[0].area_id
        self.dirty_revision += 1
        return tuple(clustered)

    def clear_clustering(self, template_area: str = "default") -> AreaModelSpec:
        """Return to the preprocessed ROI area while preserving its model and fit."""
        if template_area not in self.areas:
            raise ValueError(f"unknown template area: {template_area}")
        template = self.areas[template_area]
        self.areas = {template_area: template}
        self.reference_fits = {
            area_id: snapshot
            for area_id, snapshot in self.reference_fits.items()
            if area_id == template_area
        }
        self.model_builds = {
            area_id: snapshot
            for area_id, snapshot in self.model_builds.items()
            if area_id == template_area
        }
        self.active_area = template_area
        self.dirty_revision += 1
        return template

    def refresh_clustering_from_template(
        self,
        template_area: str = "default",
    ) -> tuple[AreaModelSpec, ...]:
        """Re-clone current cluster masks after the shared template model changes."""
        if not self.clustering_active:
            return ()
        definitions = tuple(
            AreaDefinition(
                area_id=area.area_id,
                label=area.label,
                label_value=int(area.clustering_label),
                mask=area.mask,
                mask_fingerprint=area.mask_fingerprint,
                source_kind="workspace",
                clustering_type="current",
            )
            for area_id, area in self.areas.items()
            if area_id != template_area
            and area.mask is not None
            and area.clustering_label is not None
        )
        return self.apply_clustering(definitions, template_area=template_area)

    def is_area_built(self, area_id: str) -> bool:
        area = self.areas[area_id]
        snapshot = self.model_builds.get(area_id)
        return bool(
            area.is_built
            and snapshot is not None
            and snapshot.area_revision == area.revision
            and snapshot.dataset_source_revision
            == self.dataset_identity.source_revision
            and snapshot.model_composition == area.model_composition
        )

    def commit_model_build(self, snapshot: ModelBuildSnapshot) -> AreaModelSpec:
        area = self.areas[snapshot.area_id]
        if snapshot.area_revision != area.revision:
            raise ValueError("model build belongs to a stale area revision")
        if snapshot.dataset_source_revision != self.dataset_identity.source_revision:
            raise ValueError("model build belongs to a different source")
        if snapshot.model_composition != area.model_composition:
            raise ValueError("model build composition does not match the area")
        built_area = replace(area, built_revision=area.revision)
        self.areas[area.area_id] = built_area
        self.model_builds[area.area_id] = snapshot
        self.reference_fits.pop(area.area_id, None)
        self.dirty_revision += 1
        return built_area

    def commit_reference(self, snapshot: ReferenceFitSnapshot) -> None:
        area = self.areas[snapshot.area_id]
        if not self.is_area_built(snapshot.area_id):
            raise ValueError("reference snapshot requires a current model build")
        if snapshot.area_revision != area.revision:
            raise ValueError("reference snapshot belongs to a stale area revision")
        if snapshot.dataset_source_revision != self.dataset_identity.source_revision:
            raise ValueError("reference snapshot belongs to a different source")
        self.reference_fits[snapshot.area_id] = snapshot
        self.dirty_revision += 1

    def discard_reference(self, area_id: str) -> None:
        if self.reference_fits.pop(area_id, None) is not None:
            self.dirty_revision += 1

    def invalidate_area(self, area_id: str) -> AreaModelSpec:
        return self._replace_area(self.areas[area_id])

    def invalidate_all(self) -> None:
        for area_id in tuple(self.areas):
            self.invalidate_area(area_id)

    def reset_area(self, area_id: str, template_area: str = "default") -> AreaModelSpec:
        if area_id == template_area:
            reset = AreaModelSpec(area_id=area_id, label=self.areas[area_id].label)
        else:
            template = deepcopy(self.areas[template_area])
            current = self.areas[area_id]
            reset = replace(
                template,
                area_id=area_id,
                label=current.label,
                mask=current.mask,
                mask_fingerprint=current.mask_fingerprint,
                clustering_label=current.clustering_label,
                revision=current.revision,
                built_revision=None,
                reference_strategy=current.reference_strategy,
            )
        return self._replace_area(reset)
