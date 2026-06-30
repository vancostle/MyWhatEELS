from __future__ import annotations

from typing import TYPE_CHECKING

import panel as pn

from whateels.components import InfoPanel

if TYPE_CHECKING:
    from xarray import Dataset
    from ...model import HomePageModel


NOT_AVAILABLE = "N/A"
SHAPE = "shape"
BEAM_ENERGY = "beam_energy"
CONVERGENCE_ANGLE = "convergence_angle"
COLLECTION_ANGLE = "collection_angle"
IMAGE_NAME = "image_name"

EDITABLE_METADATA_FIELDS = (
    ("Beam Energy", BEAM_ENERGY, "keV"),
    ("Convergence Angle", CONVERGENCE_ANGLE, "mrad"),
    ("Collection Angle", COLLECTION_ANGLE, "mrad"),
)

# Estilos locales del input editable.
# Se mantienen aqui para no mezclar la logica visual con el CSS global de la tarjeta.
INLINE_INPUT_STYLESHEET = """
/* The widget is forced to behave like a line of text, not a full form control. */
:host {
    height: 11px !important;
    min-height: 11px !important;
    max-height: 11px !important;
    margin: 0 !important;
    padding: 0 !important;
    transform: translateY(-6px) !important;
}
/* Flatten every wrapper Bokeh adds around the input. */
:host .bk-input-group,
:host div,
:host input,
:host .bk-input {
    height: 11px !important;
    min-height: 11px !important;
    max-height: 11px !important;
    line-height: 11px !important;
    margin: 0 !important;
    padding: 0 !important;
}
/* Keep the actual editable text compact and visually quiet. */
:host input,
:host .bk-input {
    width: 38px !important;
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;
    color: var(--panel-on-surface-color, #000) !important;
    font-family: monospace !important;
    font-size: 12px !important;
    text-align: right !important;
    vertical-align: baseline !important;
}
/* On hover/focus, only a thin underline appears so the card still feels lightweight. */
:host input:hover,
:host input:focus,
:host input:focus-visible,
:host .bk-input:hover,
:host .bk-input:focus,
:host .bk-input:focus-visible {
    border: 0 !important;
    border-bottom: 1px solid #b63fb5 !important;
    background: transparent !important;
    box-shadow: none !important;
    outline: none !important;
}
"""


def create_home_dataset_info(
    model: "HomePageModel",
    dataset: "Dataset",
    *,
    sizing_mode: str = "stretch_width",
    margin=0,
) -> InfoPanel:
    """Build the Home page metadata card with editable acquisition values."""
    attrs = dataset.attrs if dataset is not None else {}
    information = {"Shape": attrs.get(SHAPE, NOT_AVAILABLE)}

    # Los tres campos editables se construyen como widgets compactos.
    for label, attr_name, unit in EDITABLE_METADATA_FIELDS:
        information[label] = _editable_metadata_value(
            model,
            dataset,
            attr_name,
            unit,
            attrs.get(attr_name, None),
        )

    return InfoPanel(
        title="Dataset Information",
        information=information,
        sizing_mode=sizing_mode,
        margin=margin,
    )


def _editable_metadata_value(
    model: "HomePageModel",
    dataset: "Dataset",
    attr_name: str,
    unit: str,
    raw_value,
) -> pn.Row:
    # Input minimo: el valor debe leerse como texto, no como formulario pesado.
    input_widget = pn.widgets.TextInput(
        name="",
        value=_format_metadata_value(raw_value),
        placeholder=NOT_AVAILABLE,
        width=38,
        height=11,
        margin=0,
        disabled=dataset is None,
        css_classes=["dataset-info-editable-input"],
        styles={
            "height": "11px",
            "min-height": "11px",
            "max-height": "11px",
            "margin": "0",
            "padding": "0",
            "transform": "translateY(-10px)",
        },
        stylesheets=[INLINE_INPUT_STYLESHEET],
    )
    # La unidad vive aparte para poder ajustar el espaciado y la alineacion.
    unit_label = pn.pane.HTML(
        unit,
        css_classes=["dataset-info-value", "dataset-info-unit"],
        height=11,
        margin=0,
        styles={
            "height": "11px",
            "line-height": "11px",
            "display": "inline-flex",
            "align-items": "center",
            "padding": "0",
            "margin": "0",
        },
    )
    input_widget.param.watch(
        # Cada cambio actualiza el dataset y el estado compartido de la app.
        lambda event: _update_metadata_value(model, dataset, attr_name, event.new, event.obj),
        "value",
    )

    return pn.Row(
        input_widget,
        # Separador fisico para controlar la distancia entre numero y unidad.
        pn.Spacer(width=15, height=1, margin=0),
        unit_label,
        align="center",
        height=11,
        margin=(0, 0, 0, 0),
        css_classes=["dataset-info-editable-value"],
    )


def _update_metadata_value(
    model: "HomePageModel",
    dataset: "Dataset",
    attr_name: str,
    value,
    input_widget: pn.widgets.TextInput | None = None,
) -> None:
    # Si el contenido no es numerico, restauramos el valor previo del dataset.
    numeric_value = _to_optional_float(value)
    if numeric_value is None or dataset is None:
        if input_widget is not None and dataset is not None:
            input_widget.value = _format_metadata_value(dataset.attrs.get(attr_name, None))
        return

    app_state = model.app_state
    # El dataset local y el estado compartido deben apuntar al mismo valor.
    dataset.attrs[attr_name] = numeric_value
    if hasattr(app_state, "clear_elements_selected"):
        app_state.clear_elements_selected()

    all_datasets = app_state.all_datasets
    matched_dataset = False
    if isinstance(all_datasets, list):
        updated_datasets = list(all_datasets)
        for index, candidate in enumerate(updated_datasets):
            if candidate is dataset:
                candidate.attrs[attr_name] = numeric_value
                matched_dataset = True
                break

        if not matched_dataset:
            selected_index = app_state.selected_tab_index_dataset
            if 0 <= selected_index < len(updated_datasets):
                updated_datasets[selected_index].attrs[attr_name] = numeric_value

        app_state.all_datasets = updated_datasets

    # Si otras paginas estan mirando el mismo dataset, las dejamos sincronizadas.
    _update_shared_dataset_attrs(app_state.plot_dataset, dataset, attr_name, numeric_value)
    _update_shared_dataset_attrs(app_state.preprocessed_plot_dataset, dataset, attr_name, numeric_value)
    if input_widget is not None:
        input_widget.value = _format_metadata_value(numeric_value)


def _update_shared_dataset_attrs(shared_dataset, source_dataset: "Dataset", attr_name: str, value: float) -> None:
    if shared_dataset is None:
        return
    if shared_dataset is source_dataset or _same_named_dataset(shared_dataset, source_dataset):
        shared_dataset.attrs[attr_name] = value


def _same_named_dataset(candidate, source_dataset: "Dataset") -> bool:
    source_name = source_dataset.attrs.get(IMAGE_NAME)
    candidate_name = getattr(candidate, "attrs", {}).get(IMAGE_NAME)
    return bool(source_name) and source_name == candidate_name


def _to_optional_float(value) -> float | None:
    if value in (None, NOT_AVAILABLE, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_metadata_value(value) -> str:
    # Panel trabaja mejor con texto limpio; usamos formato compacto para enteros y floats.
    numeric_value = _to_optional_float(value)
    if numeric_value is None:
        return ""
    return f"{numeric_value:g}"
