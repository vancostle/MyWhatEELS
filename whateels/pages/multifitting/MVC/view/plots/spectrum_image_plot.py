"""
Spectrum image (datacube) visualization for the multifitting page.
Uses HoloViews + Panel (Bokeh backend), extends BaseSpectrumImagePlot.
"""

import panel as pn
import time

from whateels.components.info_panel import InfoPanel
from whateels.base.plots.base_spectrum_image_plot import BaseSpectrumImagePlot

from typing import override, TYPE_CHECKING
if TYPE_CHECKING:
    from ...model import MultifittingModel
    from xarray import Dataset

class SpectrumImagePlot(BaseSpectrumImagePlot):
    """
    Multifitting page spectrum image visualizer.
    Extends BaseSpectrumImagePlot (HoloViews/Panel) with inactivity-based
    hover/selection behaviour. Layout is inherited from the base class.
    create_dataset_info is overridden to read from app_state instead of dataset attrs.
    """

    _INACTIVITY_MS = 700

    def __init__(self, model: "MultifittingModel", dataset: "Dataset"):
        self._model = model

        # Inactivity state — must be set before super().__init__ triggers _setup_callbacks
        self._last_hover_ts = None
        self._pc = None

        super().__init__(dataset, eloss_name=self._model.constants.ELOSS)

    # --- create_plots inherited from BaseSpectrumImagePlot (plain SplitJs with paneA + paneB) ---

    @override
    def create_dataset_info(self) -> InfoPanel:
        NOT_AVAILABLE = 'N/A'
        ANGLE_UNIT = "mrad"
        ENERGY_UNIT = "keV"

        app_state = self._model.app_state
        all_datasets = app_state.all_datasets
        if not isinstance(all_datasets, list):
            raise ValueError("all_datasets should be a list of Dataset objects.")

        dataset = all_datasets[0]
        attrs = dataset.attrs if dataset is not None else {}

        shape = attrs.get('shape', NOT_AVAILABLE)
        beam_energy = attrs.get('beam_energy', NOT_AVAILABLE)
        convergence_angle = attrs.get('convergence_angle', NOT_AVAILABLE)
        collection_angle = attrs.get('collection_angle', NOT_AVAILABLE)

        beam_energy_fmt = f"{beam_energy} {ENERGY_UNIT}" if beam_energy != NOT_AVAILABLE else NOT_AVAILABLE
        convergence_angle_fmt = f"{convergence_angle} {ANGLE_UNIT}" if convergence_angle != NOT_AVAILABLE else NOT_AVAILABLE
        collection_angle_fmt = f"{collection_angle} {ANGLE_UNIT}" if collection_angle != NOT_AVAILABLE else NOT_AVAILABLE

        return InfoPanel(
            title="Dataset Information",
            information={
                "Shape": shape,
                "Beam Energy": beam_energy_fmt,
                "Convergence Angle": convergence_angle_fmt,
                "Collection Angle": collection_angle_fmt,
            },
            sizing_mode='stretch_width',
            margin=0,
        )

    # --- Callbacks: base streams + inactivity periodic callback ---

    @override
    def _setup_callbacks(self):
        super()._setup_callbacks()
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    # --- Inactivity logic ---

    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        if not self._region_pairs:
            if self._pc is not None and bool(self._pc.running):
                self._pc.stop()
            return

        if self._last_hover_ts is None:
            if self._pc is not None and bool(self._pc.running):
                self._pc.stop()
            self._show_spectrum(region_pairs=self._region_pairs)
            return

        if self._now_ms() - int(self._last_hover_ts) >= self._INACTIVITY_MS:
            self._show_spectrum(region_pairs=self._region_pairs)
            if self._pc is not None and bool(self._pc.running):
                self._pc.stop()

    # --- Pane A event handlers (inactivity-aware overrides) ---

    @override
    def _on_paneA_hover(self, x=None, y=None):
        if x is None or y is None:
            return
        self._queue_hover(x, y)

    def _handle_hover_render(self, point):
        if not self._region_pairs and self._try_fast_hover_update(point):
            return
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
            self._last_hover_ts = self._now_ms()
            if self._pc is not None and not bool(self._pc.running):
                self._pc.start()
        else:
            self._show_spectrum(point=point)
            if self._pc is not None and bool(self._pc.running):
                self._pc.stop()
            self._last_hover_ts = None

    @override
    def _on_paneA_click(self, x=None, y=None):
        if x is None or y is None:
            return
        self._last_hover_pixel = (round(y), round(x))
        point = {"x": x, "y": y}
        self._last_hover_point = point
        if self._region_pairs:
            self._show_spectrum(point=point, region_pairs=self._region_pairs)
            self._last_hover_ts = self._now_ms()
            if self._pc is not None and not bool(self._pc.running):
                self._pc.start()
        else:
            self._show_spectrum(point=point)
            if self._pc is not None and bool(self._pc.running):
                self._pc.stop()
            self._last_hover_ts = None

    @override
    def _on_paneA_selected(self, index=None):
        if not index:
            pairs = []
        else:
            pairs = list(dict.fromkeys(
                (idx // self._nx, idx % self._nx) for idx in index
            ))
        self._region_pairs = pairs
        self._show_spectrum(region_pairs=pairs)
        if self._pc is not None and bool(self._pc.running):
            self._pc.stop()
        self._last_hover_ts = None

    @override
    def cleanup(self):
        if self._pc is not None and bool(self._pc.running):
            self._pc.stop()
        super().cleanup()