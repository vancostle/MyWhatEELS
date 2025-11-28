"""
Spectrum line visualization composer (Plotly version).
"""
import panel as pn
import numpy as np
import plotly.graph_objs as go
import xarray as xr

from whateels.components import DatasetInformation
from whateels.interfaces import IPlot
from typing import override, TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import HomePageModel

class SpectrumLinePlot(IPlot):
    """Composes spectrum line visualizations from EELS data (Plotly)."""

    _IMAGE_X_LABEL = 'Position'
    _IMAGE_Y_LABEL = 'Energy Loss (eV)'
    _IMAGE_TITLE = 'EELS Spectrum Line'
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'
    _SPECTRUM_TITLE = 'Selected Spectrum'
    _ERR_EMPTY_ELOSS = 'Energy loss coordinates are empty'
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    _FOCUS_RATIO = 0.5
    
    def __init__(self, model: "HomePageModel", dataset: "xr.Dataset"):
        self._model = model
        self._dataset = dataset
        self._heatmap_pane = None
        self._spectrum_pane = None
        self._selected_x_value = None
        # Ranges for spectrum (preserva zoom)
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None

    @override
    def create_plots(self):
        # --- Datos base ---
        img_da = self._dataset.ElectronCount.squeeze().fillna(0.0)
        img_da = img_da.where(np.isfinite(img_da), 0.0)

        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS

        x_coords = self._dataset.coords[x_name].where(np.isfinite(self._dataset.coords[x_name]), 0.0)
        e_coords = self._dataset.coords[e_name].where(np.isfinite(self._dataset.coords[e_name]), 0.0)

        data2d = img_da.values  # shape (x, E) o (E, x); asumimos dims en orden (x, E)
        # Asegurar orden esperado: y (energía) primero para Plotly Heatmap
        if img_da.dims[0] == x_name and img_da.dims[1] == e_name:
            z = data2d.T  # pasar a (E, x)
        elif img_da.dims[0] == e_name and img_da.dims[1] == x_name:
            z = data2d  # ya (E, x)
        else:
            # fallback: intentar transponer si encuentra ambos
            z = data2d.T

        # --- Rango focal de energía (como antes) ---
        e_min = float(e_coords.min())
        e_max = float(e_coords.max())
        e_range = e_max - e_min if e_max > e_min else 1.0
        focused = e_range * self._FOCUS_RATIO
        e_center = 0.5 * (e_min + e_max)
        focus_low = e_center - focused / 2
        focus_high = e_center + focused / 2

        # --- Heatmap inicial ---
        heat = go.Heatmap(
            z=z,
            x=x_coords.values,
            y=e_coords.values,
            colorscale="Greys",
            colorbar=dict(title=self._model.constants.ELECTRON_COUNT),
            hovertemplate=f"{x_name}=%{{x}}<br>{e_name}=%{{y}}<br>I=%{{z}}<extra></extra>"
        )
        fig_hm = go.Figure(data=[heat])
        fig_hm.update_layout(
            title=self._IMAGE_TITLE,
            margin=dict(l=40, r=20, t=50, b=40),
            xaxis_title=self._IMAGE_X_LABEL,
            yaxis_title=self._IMAGE_Y_LABEL,
            yaxis=dict(autorange="reversed", range=[focus_high, focus_low]),  # invertir eje
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        self._heatmap_pane = pn.pane.Plotly(
            fig_hm.to_plotly_json(), 
            sizing_mode=self._STRETCH_BOTH, 
            config={"responsive": True}
        )
        self._heatmap_pane.param.watch(self._on_heatmap_click, "click_data")

        # --- Pane espectro vacío ---
        spec_fig = self._empty_spectrum_figure()
        self._spectrum_pane = pn.pane.Plotly(spec_fig.to_plotly_json(), sizing_mode=self._STRETCH_BOTH, config={"responsive": True})
        self._spectrum_pane.param.watch(self._on_spectrum_relayout, "relayout_data")

        return pn.Column(self._heatmap_pane, self._spectrum_pane, sizing_mode=self._STRETCH_BOTH)

    @override
    def create_dataset_info(self):
        NOT_AVAILABLE = 'N/A'
        SHAPE = 'shape'
        BEAM_ENERGY = 'beam_energy'
        COLLECTION_ANGLE = 'collection_angle'
        CONVERGENCE_ANGLE = 'convergence_angle'
        ANGLE_UNIT = "mrad"
        ENERGY_UNIT = "keV"
        
        app_state = self._model.app_state
        all_datasets = app_state.all_datasets
        if not isinstance(all_datasets, list):
            raise ValueError("all_datasets should be a list of Dataset objects.")
        
        dataset = self._dataset
        
        attrs = dataset.attrs if dataset is not None else {}

        shape = attrs.get(SHAPE, NOT_AVAILABLE)
        beam_energy = attrs.get(BEAM_ENERGY, NOT_AVAILABLE)
        convergence_angle = attrs.get(CONVERGENCE_ANGLE, NOT_AVAILABLE)
        collection_angle = attrs.get(COLLECTION_ANGLE, NOT_AVAILABLE)
        
        beam_energy = f"{beam_energy} {ENERGY_UNIT}" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle = f"{convergence_angle} {ANGLE_UNIT}" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle = f"{collection_angle} {ANGLE_UNIT}" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE
        
        dataset_information = DatasetInformation(
            title="Dataset Information", 
            information={
                "Shape": shape,
                "Beam Energy": beam_energy,
                "Convergence Angle": convergence_angle,
                "Collection Angle": collection_angle,
            },
            sizing_mode=self._STRETCH_WIDTH
        )
        
        return dataset_information

    # --- Callbacks ---
    def _on_heatmap_click(self, event):
        point = self._extract_point(event)
        if not point:
            return
        x_clicked = point["x"]
        x_name = self._model.constants.AXIS_X
        e_name = self._model.constants.ELOSS

        # Seleccionar x más cercana
        try:
            spectrum = self._dataset.ElectronCount.sel({x_name: x_clicked}, method="nearest")
        except Exception:
            return
        if 'y' in spectrum.dims:
            spectrum = spectrum.mean('y')

        energy = self._dataset.coords[e_name].values
        values = spectrum.fillna(0.0).where(np.isfinite(spectrum), 0.0).values
        self._selected_x_value = float(spectrum.coords[x_name]) if x_name in spectrum.coords else float(x_clicked)

        # Actualizar espectro
        spec_fig = go.Figure()
        spec_fig.add_trace(go.Scatter(
            x=energy,
            y=values,
            mode="lines",
            line=dict(color="crimson", width=2),
            name=f"x={self._selected_x_value}"
        ))
        spec_fig.update_layout(
            title=self._SPECTRUM_TITLE,
            margin=dict(l=40, r=20, t=50, b=40),
            xaxis_title=self._X_AXIS_SPECTRUM_TITLE,
            yaxis_title=self._Y_AXIS_SPECTRUM_TITLE,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        self._apply_current_ranges(spec_fig)
        if self._spectrum_pane is not None:
            self._spectrum_pane.object = spec_fig.to_plotly_json()

        # Redibujar línea vertical de selección en heatmap
        self._update_heatmap_selection_line()

    def _on_spectrum_relayout(self, event):
        try:
            data = event.new or {}
            if 'xaxis.range[0]' in data and 'xaxis.range[1]' in data:
                self._current_x_range = (float(data['xaxis.range[0]']), float(data['xaxis.range[1]']))
                self._current_x_autorange = False
            elif 'xaxis.autorange' in data:
                self._current_x_autorange = bool(data['xaxis.autorange'])
                if self._current_x_autorange:
                    self._current_x_range = None

            if 'yaxis.range[0]' in data and 'yaxis.range[1]' in data:
                self._current_y_range = (float(data['yaxis.range[0]']), float(data['yaxis.range[1]']))
                self._current_y_autorange = False
            elif 'yaxis.autorange' in data:
                self._current_y_autorange = bool(data['yaxis.autorange'])
                if self._current_y_autorange:
                    self._current_y_range = None
        except Exception:
            pass

    # --- Helpers ---
    def _empty_spectrum_figure(self):
        fig = go.Figure()
        fig.update_layout(
            title="Click on heatmap to extract spectrum",
            xaxis_title=self._X_AXIS_SPECTRUM_TITLE,
            yaxis_title=self._Y_AXIS_SPECTRUM_TITLE,
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    def _extract_point(self, event):
        try:
            cd = event.new
            if not cd or 'points' not in cd or not cd['points']:
                return None
            p = cd['points'][0]
            return {"x": p.get("x"), "y": p.get("y")}
        except Exception:
            return None

    def _update_heatmap_selection_line(self):
        if self._selected_x_value is None or self._heatmap_pane is None:
            return
        try:
            fig = go.Figure(self._heatmap_pane.object)  # dict -> Figure
        except Exception:
            return
        # Eliminar shapes previos tipo selección
        shapes = [s for s in fig.layout.shapes] if fig.layout.shapes else []
        shapes = [s for s in shapes if s.get("name") != "selection_line"]
        # Añadir nueva línea
        shapes.append(dict(
            type="line",
            x0=self._selected_x_value,
            x1=self._selected_x_value,
            yref="paper",
            y0=0,
            y1=1,
            line=dict(color="red", width=2, dash="dash"),
            name="selection_line"
        ))
        fig.update_layout(shapes=shapes)
        self._heatmap_pane.object = fig.to_plotly_json()

    def _apply_current_ranges(self, fig: go.Figure):
        try:
            if self._current_x_range is not None:
                fig.update_xaxes(range=self._current_x_range)
            elif self._current_x_autorange is not None:
                fig.update_xaxes(autorange=bool(self._current_x_autorange))
            if self._current_y_range is not None:
                fig.update_yaxes(range=self._current_y_range)
            elif self._current_y_autorange is not None:
                fig.update_yaxes(autorange=bool(self._current_y_autorange))
        except Exception:
            pass
        return fig
