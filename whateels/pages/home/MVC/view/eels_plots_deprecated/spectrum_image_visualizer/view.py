# ...existing code...
import panel as pn
import numpy as np
import time
from scipy.optimize import curve_fit
import plotly.graph_objs as go

pn.extension("plotly")


class SpectrumImageView:
    """
    Vista: crea panes (paneA heatmap, paneB spectrum), widgets y callbacks.
    Observa model.param.watch('dataset') para actualizar cuando cambie el modelo.
    Mantiene current ranges de paneB y aplica antes de asignar paneB.object.
    """

    # Constantes de layout/plots (centralizadas para mantenimiento)
    FIG_A_HEIGHT = 400
    FIG_B_HEIGHT = 420
    PLOT_MARGIN_A = dict(l=16, r=16, t=50, b=20)
    PLOT_MARGIN_B = dict(l=16, r=16, t=48, b=16)
    LEGEND_STYLE_LEFT = dict(
        x=0.02, y=0.98,
        xanchor="left", yanchor="top",
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="rgba(0,0,0,0.08)",
        borderwidth=1,
    )
    LEGEND_STYLE_RIGHT = dict(
        x=0.98, y=0.98,
        xanchor="right", yanchor="top",
        bgcolor="rgba(255,255,255,0.7)",
        bordercolor="rgba(0,0,0,0.08)",
        borderwidth=1,
    )
    
    def __init__(self, model, controller=None):
        self.model = model
        self.controller = controller

        # energy / data refs
        try:
            self._e_axis = self.model.dataset.coords[self.model.constants.ELOSS].values
        except Exception:
            self._e_axis = np.array([])

        self._da = getattr(self.model.dataset, "ElectronCount", None)
        self._energy = np.asarray(self._e_axis) if getattr(self._e_axis, "size", 0) else np.array([])

        # UI state
        self._current_x_range = None
        self._current_y_range = None
        self._current_x_autorange = None
        self._current_y_autorange = None

        self._region_pairs = []
        self._last_hover_point = None
        self._last_hover_ts = None
        self._INACTIVITY_MS = 500
        self._fitting_active = False

        self.range_slider = None
        self.fitting_button = None
        self.paneA = None
        self.paneB = None
        self._pc = None

        # build UI
        self._setup_widgets()
        self._update_plots_from_model()
        self._setup_callbacks()

        # subscribe to model changes
        try:
            self.model.param.watch(self._on_model_dataset_changed, 'dataset')
        except Exception:
            pass

    # ---- Model change handler ----
    def _on_model_dataset_changed(self, *events):
        try:
            self._da = getattr(self.model.dataset, "ElectronCount", None)
            self._e_axis = self.model.dataset.coords[self.model.constants.ELOSS].values
        except Exception:
            self._da = None
            self._e_axis = np.array([])
        self._energy = np.asarray(self._e_axis) if getattr(self._e_axis, "size", 0) else np.arange(self._da.shape[-1]) if self._da is not None else np.array([])
        self._update_plots_from_model()

    # ---- UI builders ----
    def _setup_widgets(self):
        self.range_slider = pn.widgets.RangeSlider(
            name="Range",
            start=float(self._e_axis[0]) if getattr(self._e_axis, "size", 0) > 0 else 0.0,
            end=float(self._e_axis[-1]) if getattr(self._e_axis, "size", 0) > 0 else 1.0,
            value=(float(self._e_axis[0]) if getattr(self._e_axis, "size", 0) > 0 else 0.0,
                   float(self._e_axis[-1]) if getattr(self._e_axis, "size", 0) > 0 else 1.0),
            sizing_mode="stretch_width",
        )
        # watcher requires _on_range_changed to exist — implemented below
        self.range_slider.param.watch(self._on_range_changed, 'value')

        self.fitting_button = pn.widgets.Button(name="fitting: OFF", button_type="primary")
        self.fitting_button.on_click(self._on_fitting_clicked)
        self.range_slider.visible = False

    def _update_plots_from_model(self):
        """Reconstruye figA y figB (manteniendo pane instances para no perder watchers)."""
        if self.model is None or getattr(self.model, "dataset", None) is None:
            return
        da = getattr(self.model.dataset, "ElectronCount", None)
        if da is None:
            return

        # integrated image
        try:
            m_image_da = da.sum(self.model.constants.ELOSS)
            m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
            if m_image.ndim != 2:
                return
            ny, nx = m_image.shape
        except Exception:
            return

        try:
            energy = np.asarray(self._e_axis)
            if energy.size != da.shape[-1]:
                energy = np.arange(da.shape[-1])
        except Exception:
            energy = np.arange(da.shape[-1])
        self._energy = energy
        self._da = da

        # figA
        heat = go.Heatmap(z=m_image, x=np.arange(nx), y=np.arange(ny), colorscale="Greys_r", showscale=False,
                          name="m_image", hovertemplate="i=%{y}, j=%{x}<br>I=%{z}<extra></extra>")
        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        selectors = go.Scattergl(x=XX.ravel(), y=YY.ravel(), mode="markers", name="selectors",
                                 marker=dict(size=6, opacity=0.01), hoverinfo="skip",
                                 selected=dict(marker=dict(opacity=0.3, size=8)),
                                 unselected=dict(marker=dict(opacity=0.01)))
        figA = go.Figure(data=[heat, selectors])
        # legend placed inside the plotting area
        figA.update_layout(
            title="m_image (hover) + lasso/box para sumar",
            height= self.FIG_A_HEIGHT,
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            legend=self.LEGEND_STYLE_LEFT
        )
        figA.update_yaxes(autorange="reversed", scaleanchor=None, constrain="domain")

        if self.paneA is None:
            self.paneA = pn.pane.Plotly(self._to_plotly(figA), config={"responsive": True})
            # watchers attached later in _setup_callbacks
        else:
            self.paneA.object = self._to_plotly(figA)

        # figB initial / selection dependent
        if self._region_pairs:
            figB = self._figB_region(self._region_pairs)
        elif self._last_hover_point is not None:
            figB = self._figB_hover(self._last_hover_point)
        else:
            figB = self._figB_message("figura_B", "mueve el ratón o selecciona")

        if self.paneB is None:
            self.paneB = pn.pane.Plotly(self._set_ranges_and_convert(figB), 
                                        height=self.FIG_B_HEIGHT, sizing_mode="fixed")
        else:
            self.paneB.object = self._set_ranges_and_convert(figB)

    # ---- helpers (subset of original) ----
    def _to_plotly(self, obj):
        try:
            if isinstance(obj, go.Figure):
                return obj.to_plotly_json()
        except Exception:
            pass
        try:
            if isinstance(obj, dict):
                if "layout" in obj and "height" not in obj["layout"]:
                    obj["layout"]["height"] = self.FIG_B_HEIGHT
                return obj
        except Exception:
            pass
        return obj

    def _figB_message(self, title, subtitle):
        fig = go.Figure()
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(title=title, height=self.FIG_B_HEIGHT, margin=self.PLOT_MARGIN_B)
        fig.add_annotation(x=0.5, y=0.6, xref="paper", yref="paper", text=subtitle, showarrow=False,
                           font=dict(size=22), align="center")
        return fig

    def _figB_hover(self, point):
        if not point:
            return self._figB_message("figura_B_hover", "hover sobre un píxel…")
        i, j = int(point["y"]), int(point["x"])
        spec = self._spectrum_from_pixel(i, j)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"(i={i}, j={j})"))
        fig.update_layout(
            title="figura_B_hover",
            height=self.FIG_B_HEIGHT,
            margin=self.PLOT_MARGIN_B,
            xaxis_title="Energía",
            yaxis_title="Intensidad",
            legend=self.LEGEND_STYLE_RIGHT
        )
        return fig

    def _figB_region(self, pairs):
        res = self._spectrum_from_indices(pairs)
        if res is None:
            return self._figB_message("figura_B_region", "selecciona con lasso/box…")
        spec, N = res
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"suma (N={N})"))
        fig.update_layout(
            title=f"figura_B_region — suma (N={N})",
            height=self.FIG_B_HEIGHT,
            margin=self.PLOT_MARGIN_B,
            xaxis_title="Energía",
            yaxis_title="Intensidad",
            legend=self.LEGEND_STYLE_RIGHT
        )
        return fig

    @staticmethod
    def powerlaw(x, A, k):
        with np.errstate(divide='ignore', invalid='ignore'):
            return A * np.power(x, k)

    def add_fit_traces(self, fig, x, y, range_values=None):
        try:
            mask = np.isfinite(x) & np.isfinite(y) & (y > 0) & (x > 0)
            if range_values is not None:
                mask &= (x >= range_values[0]) & (x <= range_values[1])
            x_f = x[mask]; y_f = y[mask]
            if x_f.size < 3:
                return fig
            params, _ = curve_fit(self.powerlaw, x_f, y_f, maxfev=10000)
            y_fit = self.powerlaw(x, *params)
            newfig = go.Figure(fig)
            newfig.add_trace(go.Scatter(x=x, y=y_fit, line=dict(color='crimson'), name='PowerLaw Fit'))
            newfig.add_trace(go.Scatter(x=x, y=(y - y_fit), fill='tozeroy',
                                       line=dict(color='rgba(255,160,122,0.2)'), fillcolor='rgba(255,160,122,0.6)',
                                       name='Background Subtraction'))
            # Place legend inside the plotting area
            newfig.update_layout(
                legend=self.LEGEND_STYLE_RIGHT
            )
            return newfig
        except Exception:
            return fig

    def _spectrum_from_pixel(self, i, j):
        try:
            return self._da.values[int(i), int(j), :].astype(float)
        except Exception:
            try:
                return self._da.values[int(j), int(i), :].astype(float)
            except Exception:
                return np.zeros(self._energy.shape)

    def _spectrum_from_indices(self, pairs):
        if not pairs:
            return None
        try:
            ii, jj = zip(*pairs)
            block = self._da.values[np.asarray(ii), np.asarray(jj), :]
            return block.sum(axis=0), len(pairs)
        except Exception:
            try:
                ii, jj = zip(*pairs)
                block = self._da.values[np.asarray(jj), np.asarray(ii), :]
                return block.sum(axis=0), len(pairs)
            except Exception:
                return None

    def _extract_point(self, data):
        try:
            if not data or "points" not in data or not data["points"]:
                return None
            p = data["points"][0]
            return {"x": p.get("x"), "y": p.get("y"), "curve": p.get("curveNumber", None)}
        except Exception:
            return None

    def _extract_region(self, data):
        try:
            if not data or "points" not in data or not data["points"]:
                return []
            pairs = []
            for p in data["points"]:
                x = p.get("x"); y = p.get("y")
                if x is None or y is None:
                    continue
                pairs.append((int(y), int(x)))
            return list(dict.fromkeys(pairs))
        except Exception:
            return []

    # ---- range/state helpers ----
    def _on_paneB_relayout(self, event):
        try:
            data = event.new or {}
            # try common keys
            if 'xaxis.range[0]' in data and 'xaxis.range[1]' in data:
                self._current_x_range = (float(data['xaxis.range[0]']), float(data['xaxis.range[1]']))
                self._current_x_autorange = False
            elif 'xaxis.range' in data:
                rng = data.get('xaxis.range')
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    self._current_x_range = (float(rng[0]), float(rng[1])); self._current_x_autorange = False
            elif 'xaxis.autorange' in data:
                self._current_x_autorange = bool(data.get('xaxis.autorange'))
                if self._current_x_autorange:
                    self._current_x_range = None

            if 'yaxis.range[0]' in data and 'yaxis.range[1]' in data:
                self._current_y_range = (float(data['yaxis.range[0]']), float(data['yaxis.range[1]']))
                self._current_y_autorange = False
            elif 'yaxis.range' in data:
                rng = data.get('yaxis.range')
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    self._current_y_range = (float(rng[0]), float(rng[1])); self._current_y_autorange = False
            elif 'yaxis.autorange' in data:
                self._current_y_autorange = bool(data.get('yaxis.autorange'))
                if self._current_y_autorange:
                    self._current_y_range = None
        except Exception:
            pass

    def _apply_current_ranges(self, fig):
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

    def _set_ranges_and_convert(self, fig):
        try:
            fig_obj = fig if isinstance(fig, go.Figure) else go.Figure(fig)
        except Exception:
            fig_obj = go.Figure()
        self._apply_current_ranges(fig_obj)
        return self._to_plotly(fig_obj)

    # ---- events from paneA (hover/click/select) and timers ----
    def _check_inactivity(self):
        if not self._region_pairs:
            if self._pc.running:
                self._pc.stop()
            return
        if self._last_hover_ts is None:
            if self._pc.running:
                self._pc.stop()
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = self._spectrum_from_indices(self._region_pairs)
                if res is not None:
                    spec, _ = res
                    fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return
        if self._now_ms() - int(self._last_hover_ts) >= self._INACTIVITY_MS:
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = self._spectrum_from_indices(self._region_pairs)
                if res is not None:
                    spec, _ = res
                    fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            if self._pc.running:
                self._pc.stop()

    def _now_ms(self):
        return int(time.time() * 1000)

    def _on_paneA_hover(self, event):
        point = self._extract_point(event.new)
        if point is None:
            return
        self._last_hover_point = point
        if self._region_pairs:
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                i, j = int(point["y"]), int(point["x"])
                spec = self._spectrum_from_pixel(i, j)
                if spec is not None:
                    fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()
        else:
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                i, j = int(point["y"]), int(point["x"])
                spec = self._spectrum_from_pixel(i, j)
                if spec is not None:
                    fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None

    def _on_paneA_click(self, event):
        point = self._extract_point(event.new)
        if point is None:
            return
        self._last_hover_point = point
        fig = self._figB_hover(self._last_hover_point)
        if self._fitting_active:
            i, j = int(point["y"]), int(point["x"])
            spec = self._spectrum_from_pixel(i, j)
            if spec is not None:
                fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
        self.paneB.object = self._set_ranges_and_convert(fig)
        if self._region_pairs:
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()
        else:
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None

    def _on_paneA_selected(self, event):
        pairs = self._extract_region(event.new)
        self._region_pairs = pairs
        if not pairs:
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                fig = self._figB_hover(self._last_hover_point)
                if self._fitting_active:
                    i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
                    spec = self._spectrum_from_pixel(i, j)
                    if spec is not None:
                        fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
                self.paneB.object = self._set_ranges_and_convert(fig)
            else:
                self.paneB.object = self._set_ranges_and_convert(self._figB_message("figura_B", "mueve el ratón o selecciona"))
            return
        fig = self._figB_region(self._region_pairs)
        if self._fitting_active:
            res = self._spectrum_from_indices(self._region_pairs)
            if res is not None:
                spec, _ = res
                fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
        self.paneB.object = self._set_ranges_and_convert(fig)
        if self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None

    # ---- setup callbacks / periodic callback ----
    def _setup_callbacks(self):
        if self.paneA is not None:
            self.paneA.param.watch(self._on_paneA_hover, "hover_data")
            self.paneA.param.watch(self._on_paneA_click, "click_data")
            self.paneA.param.watch(self._on_paneA_selected, "selected_data")
        if self.paneB is not None:
            self.paneB.param.watch(self._on_paneB_relayout, "relayout_data")
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    # ---- handlers for fitting/range UI (previously missing) ----
    def _on_fitting_clicked(self, event):
        self._fitting_active = not self._fitting_active
        self.fitting_button.name = f"fitting: {'ON' if self._fitting_active else 'OFF'}"
        self.fitting_button.button_type = "danger" if self._fitting_active else "primary"
        self.range_slider.visible = self._fitting_active

        # Refresh current view
        if self._region_pairs:
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = self._spectrum_from_indices(self._region_pairs)
                if res is not None:
                    spec, _ = res
                    fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return

        if self._last_hover_point is not None:
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
                spec = self._spectrum_from_pixel(i, j)
                if spec is not None:
                    fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return

        self.paneB.object = self._set_ranges_and_convert(self._figB_message("Fitting", "Modo fitting: " + ("activado" if self._fitting_active else "desactivado")))

    def _on_range_changed(self, event):
        """Refresh paneB when the fit range slider changes (only when fitting is active)."""
        if not self._fitting_active:
            return
        if self._region_pairs:
            fig = self._figB_region(self._region_pairs)
            res = self._spectrum_from_indices(self._region_pairs)
            if res is not None:
                spec, _ = res
                fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return
        if self._last_hover_point is not None:
            fig = self._figB_hover(self._last_hover_point)
            i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
            spec = self._spectrum_from_pixel(i, j)
            if spec is not None:
                fig = self.add_fit_traces(fig, self._energy, spec, range_values=self.range_slider.value)
            self.paneB.object = self._set_ranges_and_convert(fig)

    # ---- public builders ----
    def create_plots(self):
        right_col = pn.Column(self.paneB, self.fitting_button, self.range_slider, sizing_mode="stretch_width")
        return pn.Column(pn.Row(self.paneA, right_col, sizing_mode="stretch_width"), sizing_mode="stretch_width")

    def create_dataset_info(self):
        attrs = self.model.dataset.attrs if self.model.dataset is not None else {}
        shape = attrs.get('shape', 'N/A')
        beam_energy = attrs.get('beam_energy', 'N/A')
        convergence_angle = attrs.get('convergence_angle', 'N/A')
        collection_angle = attrs.get('collection_angle', 'N/A')
        buttonIcon = pn.widgets.ButtonIcon(icon="plus", size="1.8rem", description="All file info")
        if self.controller is not None and getattr(self.controller, "layout", None) is not None:
            buttonIcon.on_click(lambda e: self.controller.layout.toggle_float_panel())
        header = pn.Row(pn.pane.HTML("<h5 class=\"dataset-info-title\">Dataset Information</h5>", sizing_mode="stretch_width"),
                        buttonIcon, sizing_mode="stretch_width", css_classes=["dataset-info-header"])
        dataset_info = pn.Column(header, pn.Spacer(height=5),
                                 pn.Row(pn.pane.Str("Shape:"), pn.pane.Str(shape), sizing_mode="stretch_width"),
                                 pn.Row(pn.pane.Str("Beam Energy:"), pn.pane.Str(f"{beam_energy} keV"), sizing_mode="stretch_width"),
                                 pn.Row(pn.pane.Str("Convergence Angle:"), pn.pane.Str(f"{convergence_angle} mrad"), sizing_mode="stretch_width"),
                                 pn.Row(pn.pane.Str("Collection Angle:"), pn.pane.Str(f"{collection_angle} mrad"), sizing_mode="stretch_width"),
                                 sizing_mode="stretch_width", css_classes=["dataset-info", "animated"])
        return dataset_info
# ...existing code...