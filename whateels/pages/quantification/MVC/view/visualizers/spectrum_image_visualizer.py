"""
Spectrum image (datacube) visualization composer.
Se reemplaza HoloViews por Panel + Plotly usando la lógica de si_view.py,
pero manteniendo la lógica de acceso a datos y widgets de SpectrumImageVisualizer.
"""

import panel as pn
import numpy as np
import time
import plotly.graph_objs as go

from .abstract_eels_visualizer import AbstractEELSVisualizer
from typing import override, TYPE_CHECKING
from whateels.helpers import SpectrumExtractor, SpectrumFitting
from whateels.components import ResizableColumns
from whateels.shared_state import AppState
from ...controller.services.oos_loader_service import Loader_OOS

if TYPE_CHECKING:
    from ...model import Model
    from xarray import Dataset
    from param.parameterized import Event

class add_cs:
    """
    Class to calculate and normalize cross-sections for a given element and shell.
    """
    def __init__(self, element, ishell, selected_slice, y_extrapolated, chemical_shift=0, quant_range_values=None, eaxis=None, eaxis_cs=None, counts=None, onset=None, cross_section=None):
        """
        Initializes the add_cs object.

        Parameters:
            element: The element name (e.g., "Fe").
            ishell: The shell name (e.g., "K").
            selected_slice: The selected slice of data.
            y_extrapolated: The extrapolated background values.
            chemical_shift: The chemical shift to apply (default is 0).
            quant_range_values: The range of energy for quantification.
            eaxis: The energy axis for the experimental data.
            eaxis_cs: The energy axis for the cross-section data.
            counts: The counts data.
            onset: The onset energy.
            cross_section: The cross-section data.
        """
        self.eaxis, self.counts, self.onset = eaxis, counts, onset
        self.cross_section = cross_section
        self.element = element
        self.ishell = ishell
        self.chemical_shift = chemical_shift
        self.quant_range_values = quant_range_values
        self.eaxis_cs = eaxis_cs

        # Ensure that the lengths of the energy axes and data match
        if len(eaxis) != len(selected_slice) and len(eaxis_cs) != len(cross_section):
            raise ValueError("eaxis, selected_slice, and cross_section must have the same length.")

        # Normalize the experimental and simulated data within the quantification range
        if self.quant_range_values:
            mask = (self.eaxis >= self.quant_range_values[0]) & (self.eaxis <= self.quant_range_values[1])
            mask_ = (self.eaxis_cs >= self.quant_range_values[0]) & (self.eaxis_cs <= self.quant_range_values[1])
            x_filtered = self.eaxis[mask]
            y_filtered = selected_slice[mask] - y_extrapolated[mask]
            x_filtered_ = self.eaxis_cs[mask_]
            y_filtered_ = self.cross_section[mask_]
            self.norm_exp = np.trapz(y_filtered, x_filtered).real  # Experimental normalization
            self.norm_sim = np.trapz(y_filtered_, x_filtered_).real  # Simulated normalization
        else:
            self.norm_sim = np.trapz(self.cross_section, self.eaxis).real
            self.norm_exp = np.trapz(selected_slice - y_extrapolated, self.eaxis).real

        # Apply the chemical shift and calculate the normalized cross-section
        self.xaxis = self.eaxis_cs - self.chemical_shift
        self.yaxis = (self.cross_section / self.norm_sim * self.norm_exp).real

    def get_data(self):
        """
        Returns the calculated data for plotting.

        Returns:
            xaxis: The shifted energy axis.
            yaxis: The normalized cross-section.
        """
        return self.xaxis, self.yaxis

def sum_slice(matrix, vertexs):
    """
    Sums the values in a region defined by vertices in a matrix.

    Parameters:
        matrix: The 2D matrix to sum over.
        vertexs: A tuple (x_start, x_end, y_start, y_end) defining the region.

    Returns:
        The sum of the values in the specified region.
    """
    suma = 0
    for i in range(vertexs[0], vertexs[1]):
        for j in range(vertexs[2], vertexs[3]):
            suma += matrix[j][i]
    return suma

class quanti:
    """
    Class to calculate quantification between two regions.
    """
    def __init__(self, d_a, d_b, cs_a, cs_b, y1, y2, eaxis):
        """
        Initializes the quanti object.

        Parameters:
            d_a, d_b: Energy ranges for the two regions.
            cs_a, cs_b: Cross-section data for the two regions.
            y1, y2: Experimental data for the two regions.
            eaxis: The energy axis.
        """
        self.y1 = y1
        self.y2 = y2
        self.d_a = d_a
        self.d_b = d_b
        self.cs_b_x, self.cs_b_y = cs_b
        self.cs_a_x, self.cs_a_y = cs_a
        self.eaxis = eaxis

    def get_part_delta(self, y, axis, delta):
        """
        Calculates the integral of a portion of the data within a specified range.

        Parameters:
            y: The data to integrate.
            axis: The corresponding axis.
            delta: The range for integration.

        Returns:
            The integral value.
        """
        mask = (axis >= delta[0]) & (axis <= delta[1])
        return np.trapz(y[mask], axis[mask]).real

    def get_quanti(self):
        """
        Calculates the quantification ratio between two regions.

        Returns:
            The quantification ratio (q_ab).
        """
        i_a = self.get_part_delta(self.y1, self.eaxis, self.d_a)
        i_b = self.get_part_delta(self.y2, self.eaxis, self.d_b)
        cs_a = self.get_part_delta(self.cs_a_y, self.cs_a_x, self.d_a)
        cs_b = self.get_part_delta(self.cs_b_y, self.cs_b_x, self.d_b)
        self.q_ab = i_a / i_b * cs_b / cs_a
        return self.q_ab

def get_envelope(x1, y1, x2, y2):
    """
    Calculates the envelope of two curves.

    Parameters:
        x1, y1: The x and y values of the first curve.
        x2, y2: The x and y values of the second curve.

    Returns:
        x_common: The common x values.
        y_envelope: The envelope (maximum y values at each x).
    """
    # Find the common x range
    x_common = np.union1d(x1, x2)

    # Interpolate y values for the common x points
    y1_interp = np.interp(x_common, x1, y1)
    y2_interp = np.interp(x_common, x2, y2)

    # Calculate the envelope by taking the maximum at each point
    y_envelope = np.maximum(y1_interp, y2_interp)
    return x_common, y_envelope

class SpectrumImageVisualizer(AbstractEELSVisualizer):
    """
    Version Plotly / Panel del visualizador de Spectrum Image.
    Mantiene la lógica de datos del visualizador original y reemplaza
    HoloViews por Plotly panes y callbacks (hover / click / select).
    """
    
    # Panel sizing modes
    _STRETCH_WIDTH = "stretch_width"
    
    # CSS classes and constants for dataset info panel
    _DATASET_INFO_HEADER_CLASS = ["dataset-info-header"]
    _DATASET_INFO_CLASS = ["dataset-info", "animated"]
    _DATASET_INFO_TITLE = "<h5 class=\"dataset-info-title\">Dataset Information</h5>"
    
    _NOT_AVAILABLE = 'N/A'
    
    # Axis titles for spectrum plot
    _X_AXIS_SPECTRUM_TITLE = 'Energy Loss (eV)'
    _Y_AXIS_SPECTRUM_TITLE = 'Intensity (a.u.)'

    def __init__(self, model: "Model", dataset: "Dataset"):
        super().__init__(model, dataset)

        self._model = model
        self._dataset = dataset

        # Energy axis (eje de energía)
        self._e_axis = self._dataset.coords[self._model.constants.ELOSS].values

        # ElectronCount data cube
        self._electron_count_data: "Dataset" = self._dataset.ElectronCount
        
        # Last selected pixel (x,y)
        self._last_selected = {"x": 0, "y": 0}

        # Range state for paneB (to preserve zoom/pan)
        self._current_x_range = None
        self._current_y_range = None
        # None = unknown / leave Plotly default; True/False = explicitly requested autorange
        self._current_x_autorange = None
        self._current_y_autorange = None

        # Selection / hover / fitting state (inspired by si_view.py)
        self._region_pairs = []         # lista de (i,j) seleccionados por lasso/box
        self._last_hover_point = None   # último hover {x,y,curve}
        self._last_hover_ts = None
        self._INACTIVITY_MS = 700
        self._fitting_active = False

        # Widgets / panes placeholders
        self.range_slider = None
        self.fitting_button = None
        self.paneA = None  # Plotly heatmap pane
        self.paneB = None  # Plotly spectrum pane
        self._pc = None    # periodic callback handle
        self._js_executor = None  # invisible HTML pane to run JS

        self.element_quant_data = []  # to store quantification data per element

        # Setup widgets, plots and callbacks
        self._setup_widgets()
        self._setup_plots()
        self._setup_callbacks()

    def get_e_axis(self):
        return self._e_axis
        
    # --- Public layout builders (used by controller) ---
    @override
    def create_plots(self):        
        left_column = pn.Column(
            self.paneA,
            sizing_mode='stretch_both'
        )
        
        right_column = pn.Column(
            self.paneB,
            # fila de botones (fitting + multifit)
            self.buttons_row if hasattr(self, 'buttons_row') else self.fitting_button,
            # slider/range debajo
            self.range_slider_row if hasattr(self, 'range_slider_row') else self.range_slider,
            sizing_mode='stretch_both'
        )
        
        resizable_columns = ResizableColumns(
            left_column=left_column,
            right_column=right_column,
            sizing_mode='stretch_both',
        )
 
        return resizable_columns

    @override
    def create_dataset_info(self):
        return super().create_dataset_info()
    




    def plot_quantification_elements(self, loader_OOS : "Loader_OOS", element_items: list):
        """Placeholder method to match abstract base class."""
        fig = self._figB_region(self._region_pairs)
        fig = self._to_plotly(fig)
        
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
        if res is not None:
            selected_slice, _ = res
            

            if element_items:
                i = 0
                for element_item in element_items:
                    fig = self.plot_element(fig, loader_OOS, selected_slice, element_item)
        
        self.paneB.object = self._set_ranges_and_convert(fig)
        return self.element_quant_data

    def plot_element(self, fig, loader_OOS : "Loader_OOS", selected_slice, element_item : "ElementItem"):
        print("Selected slice obtained")
        print("Element item:", element_item)
        print("State shells and element:", element_item.shells, element_item.element)
        print("Energy axis:", self._energy)
        print("E axis:", self._e_axis)
        if element_item and element_item.element and element_item.shells:
            try:
                shells_data = []
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, selected_slice, range_values=element_item.fit_range)
                fig = self._plot_fit_traces(fig, self._energy, selected_slice, y_fit)
                for ishell in element_item.shells:
                    fig, shell_data = self.calculate_shell_data(fig, loader_OOS, selected_slice, element_item, y_fit, ishell)
                    shells_data.append((ishell, shell_data))
                    print(f"Quantification for {element_item.element} {ishell} added.")
                if len(shells_data) == 2:
                    ##afegir element data a init
                    self.element_quant_data.append([
                                    element_item, y_fit,
                                    get_envelope(
                                        shells_data[0][1][0], shells_data[0][1][1],
                                        shells_data[1][1][0], shells_data[1][1][1]
                                    )
                                ])
                else:
                    self.element_quant_data.append([element_item, y_fit, shells_data[0][1]])
            except Exception as e:
                raise e
        fig.update_layout(xaxis= dict(range=[self._e_axis[0], self._e_axis[-1]]))
        return fig

    def calculate_shell_data(self, fig, loader_OOS, selected_slice, element_item, y_extrapolated, ishell):
        eaxis, counts, onset = loader_OOS.oos_reader(element_item.element, ishell)
        V = self._dataset.attrs['beam_energy']
        b = self._dataset.attrs['collection_angle']
        cross_section = loader_OOS.df_cross_section(element_item.element, ishell, V = V, b = b)
        fig, shell_data = self.plot_cs(
                                    fig, element_item, ishell, selected_slice, y_extrapolated,
                                    eaxis_cs=eaxis, counts=counts, onset=onset,
                                    cross_section=cross_section, chemical_shift=16
                                )
                    
        return fig,shell_data
    
    def plot_cs(self, fig, element_item, ishell, selected_slice, y_extrapolated, eaxis_cs, counts, onset, cross_section, chemical_shift=16):
        
        cs_instance = add_cs(
                    element=element_item.element, 
                    ishell=ishell, 
                    selected_slice=selected_slice, 
                    y_extrapolated=y_extrapolated, 
                    chemical_shift=chemical_shift, 
                    quant_range_values=element_item.quant_range, 
                    eaxis=self._e_axis, 
                    eaxis_cs=eaxis_cs, 
                    counts=counts, 
                    onset=onset, 
                    cross_section=cross_section
            )
    
        xaxis, yaxis = cs_instance.get_data()
        fig.add_trace(go.Scatter(
            x=xaxis, 
            y=yaxis, 
            name=f'{cs_instance.element} {cs_instance.ishell} OOS'
        ))
        fig.update_layout(xaxis=dict(range=[self._e_axis, self._e_axis]))

        return fig, (xaxis, yaxis)
    
    def plot_quantification_pie(self, element_data):
        """
        Calculates the quantification results for the elements in the state.

        Parameters:
            state: The application state containing element data and energy information.

        Returns:
            A string summarizing the quantification results or an error message if something goes wrong.
        """
        try:
            q_list = []  # List to store quantification results
            print("Element data count:", len(element_data))
            i = 0
            # Iterate through the element data list in pairs
            while i < len(element_data) - 1:
                print(i, len(element_data))
                # Extract data for the current and next elements
                element_item0, y_extrapolated0, element_data0 = element_data[i]
                element_item1, y_extrapolated1, element_data1 = element_data[i + 1]
                
                # Perform quantification between the two elements
                q_aux = quanti(
                    element_item0.quant_range, element_item1.quant_range,
                    element_data0, element_data1,
                    y_extrapolated0, y_extrapolated1,
                    self._energy
                ).get_quanti()
                
                # Check if the quantification result is valid
                if q_aux < 0:
                    return f" | Quantification result: Negative value for {element_item0.element} / {element_item1.element}, check ranges."
                else:
                    # Append the result to the list
                    q_list.append((element_item0.element, element_item1.element, q_aux))
                i += 1

            print("Quantification results:", q_list)
            ##state.paneC.object = pie_plot(q_list)  # Update the pie chart with the results
            self.paneB.object = self._set_ranges_and_convert(self.pie_plot(q_list))
            return f" | Quantification result: {q_list}"
        except Exception as e:
            # Handle any errors that occur during quantification
            print("Error in quantification calculation:", e)
            return f" | Error in quantification calculation: {e}"

    def pie_plot(self, q_list):
        """
        Creates a pie chart to visualize the quantification results.

        Parameters:
            q_list: A list of tuples containing element pairs and their quantification values.

        Returns:
            A Plotly pie chart figure.
        """
        A = 1  # Initial value for proportions
        abc_list = [1]  # List to store intermediate proportions
        for i in range(len(q_list)):
            # Calculate the proportion for each element pair
            abc_list.append(abc_list[i] / q_list[i][2])

        # Normalize the proportions
        total = sum(abc_list)
        proportions = []  # List to store normalized proportions
        labels = []  # List to store labels for the pie chart
        for i in range(len(abc_list)):
            proportions.append(abc_list[i] / total)
            if i != len(abc_list) - 1:
                labels.append(q_list[i][0])  # Add the first element of the pair as a label
        labels.append(q_list[-1][1])  # Add the last element of the last pair as a label

        print("Proportions:", proportions)
        # Create the pie chart using Plotly
        fig = go.Figure(data=[go.Pie(labels=labels, values=proportions, hole=0.0)])
        return fig


    

    # --- Widget Setup (kept from original, but range_slider reused) ---
    def _setup_widgets(self):
        # Range slider ya usado por la implementación anterior  
        self.range_slider = pn.widgets.EditableRangeSlider(
            name="",  # label externo controlado manualmente
            start=float(self._e_axis[0]) if len(self._e_axis) > 0 else 0.0,
            end=float(self._e_axis[-1]) if len(self._e_axis) > 0 else 1.0,
            value=(float(self._e_axis[0]), float(self._e_axis[-1])),
            sizing_mode=self._STRETCH_WIDTH,
        )
        # Apply our CSS class to style the widget
        self.range_slider.css_classes = ["my-range"]
        self.range_slider.param.watch(self._on_range_changed, 'value')

        # Fitting toggle button
        self.fitting_button = pn.widgets.Button(name="Fitting: OFF", button_type="primary")
        self.fitting_button.on_click(self._on_fitting_clicked)

        # Multifit button (orange)
        self.multifit_button = pn.widgets.Button(name="Multifit", button_type="warning")
        self.multifit_button.on_click(self._on_multifit_clicked)  # server-side fallback
        self.multifit_button.visible = False

        # Invisible HTML pane to run JavaScript (Open new window with params)
        self._js_executor = pn.pane.HTML("", width=0, height=0)

        # Fila de botones debajo de paneB
        self.buttons_row = pn.Row(
            self.fitting_button,
            self.multifit_button,
            self._js_executor,
            sizing_mode=self._STRETCH_WIDTH
        )

        # Fila con label y slider para alineación limpia
        self.range_slider_row = pn.Row(
            pn.pane.Markdown("**Range:**", sizing_mode="fixed", width=60, css_classes=["range-label"]),
            self.range_slider,
            sizing_mode=self._STRETCH_WIDTH,
            css_classes=["range-label-wrapper"],
        )
        self.range_slider_row.visible = False

    def _on_multifit_clicked(self, event):
        """Callback para el botón de multifit"""
        # Publish the dataset now that multifit is requested.
        try:
            AppState().plot_dataset = self._dataset
        except Exception:
            print("Error publishing dataset to AppState for multifit.")
        
        min_val, max_val = self.range_slider.value
        
        url_base = f"http://{pn.state.location.hostname}:{pn.state.location.port}"

        values = f"{min_val},{max_val}"
        url_with_params = f"{url_base}/multifit-details?values={values}"

        self._js_executor.object = f"""
            <script>
                window.open('{url_with_params}', '_blank');
            </script>
        """

    def _on_range_changed(self, event):
        """Refresh paneB when the fit range slider changes (only when fitting is active)."""
        if not self._fitting_active:
            return
        if self._region_pairs:
            fig = self._figB_region(self._region_pairs)
            res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
            if res is not None:
                spec, _ = res
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return
        if self._last_hover_point is not None:
            fig = self._figB_hover(self._last_hover_point)
            i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
            spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
            if spec is not None:
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)


    # --- Plot / Pane Setup (Plotly) ---
    def _setup_plots(self):
        # Build image (m_image) from data cube in the canonical way used in this class
        # ElectronCount dims assumed (y, x, E)
        # Use self._electron_count_data from constructor
        m_image_da = self._electron_count_data.sum(self._model.constants.ELOSS)
        m_image = np.asarray(m_image_da.fillna(0.0).where(np.isfinite(m_image_da), 0.0))
        if m_image.ndim != 2:
            raise ValueError(f"Se esperaba imagen 2D integrada, recibido shape={m_image.shape}")

        ny, nx = m_image.shape
        # energy axis
        try:
            energy = np.asarray(self._e_axis)
            if energy.shape[0] != self._electron_count_data.shape[-1]:
                energy = np.arange(self._electron_count_data.shape[-1])
        except Exception:
            energy = np.arange(self._electron_count_data.shape[-1])
        self._energy = energy

        # Build Plotly heatmap (figA) and selectors scatter for box/lasso selections
        heat = go.Heatmap(
            z=m_image,
            x=np.arange(nx),
            y=np.arange(ny),
            colorscale="Greys_r",
            showscale=False,
            name="m_image",
            hovertemplate="i=%{y}, j=%{x}<br>I=%{z}<extra></extra>",
        )

        XX, YY = np.meshgrid(np.arange(nx), np.arange(ny))
        selectors = go.Scattergl(
            x=XX.ravel(),
            y=YY.ravel(),
            mode="markers",
            name="selectors",
            marker=dict(size=6, opacity=0.01),
            hoverinfo="skip",
            selected=dict(marker=dict(opacity=0.3, size=8)),
            unselected=dict(marker=dict(opacity=0.01)),
        )

        # Create figure with default size but lock aspect ratio so it doesn't deform
        figA = go.Figure(data=[heat, selectors])
        figA.update_layout(
            title=" ",
            height=400,  # default initial height as in the original copy
            margin=dict(l=16, r=16, t=50, b=20),
            dragmode="lasso",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        # Keep origin top-left and preserve 1:1 pixel aspect to avoid deformation
        figA.update_yaxes(autorange="reversed", scaleanchor="x", scaleratio=1, constrain="domain",
                           showgrid=False, zeroline=False, showticklabels=False)
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, constrain="domain")

        # Pane A (heatmap) — responsive and will scale to parent; aspect locked by figure axes
        self.paneA = pn.pane.Plotly(self._to_plotly(figA), config={"responsive": True}, sizing_mode='stretch_both')

        # Pane B initial message (apply stored ranges if any)
        self.paneB = pn.pane.Plotly(
            self._set_ranges_and_convert(self._figB_message(" ", "Move the cursor over the image")),
            sizing_mode='stretch_both', config={"responsive": True}
        )

    # --- Callbacks setup (connect pane watchers & periodic callback) ---
    def _setup_callbacks(self):
        # Attach panel watchers to figA and paneB
        self.paneA.param.watch(self._on_paneA_hover, "hover_data")
        self.paneA.param.watch(self._on_paneA_click, "click_data")
        self.paneA.param.watch(self._on_paneA_selected, "selected_data")

        # relayout_data is emitted by pn.pane.Plotly on axis changes
        self.paneB.param.watch(self._on_paneB_relayout, "relayout_data")

        # Periodic callback for inactivity logic (stopped by default)
        self._pc = pn.state.add_periodic_callback(self._check_inactivity, period=250, start=False)

    # --- Helpers / utilities (from si_view.py adapted) ---
    def _to_plotly(self, obj):
        """Convert go.Figure to dict to avoid Panel<->Plotly relayout issues."""
        try:
            if isinstance(obj, go.Figure):
                return obj.to_plotly_json()
        except Exception:
            pass
        try:
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
        return obj

    def _figB_message(self, title, subtitle):
        fig = go.Figure()
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(title=title, margin=dict(l=16, r=16, t=48, b=16))
        fig.add_annotation(
            x=0.5, y=0.6, xref="paper", yref="paper",
            text=subtitle, showarrow=False,
            font=dict(size=22), align="center",
        )
        return fig

    def _figB_hover(self, point):
        if not point:
            return self._figB_message("Hover", "Move the cursor over the image")
        i, j = int(point["y"]), int(point["x"])
        spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"(i={i}, j={j})"))
        fig.update_layout(title="Hover", margin=dict(l=16, r=16, t=48, b=16),
                          xaxis_title=self._X_AXIS_SPECTRUM_TITLE, yaxis_title=self._Y_AXIS_SPECTRUM_TITLE)
        return fig

    def _figB_region(self, pairs):
        res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, pairs)
        if res is None:
            return self._figB_message("ROI", "Select with lasso/box...")
        spec, n_points = res
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=self._energy, y=spec, mode="lines", name=f"sum (points={n_points})"))
        fig.update_layout(
            title=f"ROI — sum (points={n_points})",
            margin=dict(l=16, r=16, t=48, b=16), 
            xaxis_title=self._X_AXIS_SPECTRUM_TITLE, 
            yaxis_title=self._Y_AXIS_SPECTRUM_TITLE
        )
        return fig

    # --- Inactivity logic (restaurar selección tras inactivity) ---
    def _now_ms(self):
        return int(time.time() * 1000)

    def _check_inactivity(self):
        # No selection -> nothing to do
        if not self._region_pairs:
            if self._pc.running:
                self._pc.stop()
            return

        # If there is no hover timestamp, ensure selection is shown and timer stopped
        if self._last_hover_ts is None:
            if self._pc.running:
                self._pc.stop()
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
                if res is not None:
                    spec, _N = res
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return

        if self._now_ms() - int(self._last_hover_ts) >= self._INACTIVITY_MS:
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
                if res is not None:
                    spec, _N = res
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
            if self._pc.running:
                self._pc.stop()
                
    def _plot_fit_traces(self, fig, x, y, y_fit):
        """
        Add fit and background subtraction traces to a Plotly figure.

        Parameters:
            fig (plotly.graph_objs.Figure): The Plotly figure to add traces to.
            x (array-like): Independent variable data.
            y (array-like): Dependent variable data.
            y_fit (array-like): Fitted curve values for all x.

        Returns:
            plotly.graph_objs.Figure: The figure with added fit and subtraction traces.
        """
        # Local constants for Plotly and fitting
        POWERLAW_FIT_NAME = 'PowerLaw Fit'
        BG_SUBTRACTION_NAME = 'Background Subtraction'
        CRIMSON = 'crimson'
        BG_LINE_COLOR = 'rgba(255,160,122,0.2)'
        BG_FILL_COLOR = 'rgba(255,160,122,0.6)'
        LEGEND_X = 0.98
        LEGEND_Y = 0.98
        LEGEND_XANCHOR = 'right'
        LEGEND_YANCHOR = 'top'
        LEGEND_BGCOLOR = 'rgba(255,255,255,0.6)'
        LEGEND_BORDER_COLOR = 'rgba(0,0,0,0.1)'
        LEGEND_BORDER_WIDTH = 1
        FILL_TO_ZEROY = 'tozeroy'

        if y_fit is None:
            return fig
        newfig = go.Figure(fig)
        newfig.add_trace(go.Scatter(
            x=x,
            y=y_fit,
            line=dict(color=CRIMSON),
            name=POWERLAW_FIT_NAME
        ))
        newfig.add_trace(go.Scatter(
            x=x,
            y=(y - y_fit),
            fill=FILL_TO_ZEROY,
            line=dict(color=BG_LINE_COLOR),
            fillcolor=BG_FILL_COLOR,
            name=BG_SUBTRACTION_NAME
        ))
        newfig.update_layout(
            legend=dict(
                x=LEGEND_X,
                y=LEGEND_Y,
                xanchor=LEGEND_XANCHOR,
                yanchor=LEGEND_YANCHOR,
                bgcolor=LEGEND_BGCOLOR,
                bordercolor=LEGEND_BORDER_COLOR,
                borderwidth=LEGEND_BORDER_WIDTH,
            )
        )
        return newfig

    # --- Pane A event handlers (hover / click / selected) ---
    def _on_paneA_hover(self, event: "Event"):
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        if self._region_pairs:
            # Temporary hover while a selection exists: show hover spectrum and start/renew timer
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                i, j = int(point["y"]), int(point["x"])
                spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
                if spec is not None:
                    y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                    fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)  
            self.paneB.object = self._set_ranges_and_convert(fig)
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()
        else:
            # No selection: persistent hover view, no inactivity timer
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                i, j = int(point["y"]), int(point["x"])
                spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
                if spec is not None:
                    y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                    fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None

    def _on_paneA_click(self, event):
        point = SpectrumExtractor.extract_point(event)
        if point is None:
            return
        self._last_hover_point = point
        fig = self._figB_hover(self._last_hover_point)
        if self._fitting_active:
            i, j = int(point["y"]), int(point["x"])
            spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
            if spec is not None:
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
        if self._region_pairs:
            self._last_hover_ts = self._now_ms()
            if not self._pc.running:
                self._pc.start()
        else:
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None

    def _on_paneA_selected(self, event: "Event"):
        pairs = SpectrumExtractor.extract_region(event)
        self._region_pairs = pairs
        if not pairs:
            if self._pc.running:
                self._pc.stop()
            self._last_hover_ts = None
            if self._last_hover_point is not None:
                fig = self._figB_hover(self._last_hover_point)
                if self._fitting_active:
                    y, x = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
                    spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, y, x)
                    if spec is not None:
                        y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                        fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
                    self.paneB.object = self._set_ranges_and_convert(fig)
            else:
                self.paneB.object = self._set_ranges_and_convert(self._figB_message(" ", "Move the cursor over the image"))
            return

        fig = self._figB_region(self._region_pairs)
        if self._fitting_active:
            res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
            if res is not None:
                spec, N = res
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
        self.paneB.object = self._set_ranges_and_convert(fig)

        # prepare inactivity behaviour: stop periodic callback until next hover
        if self._pc.running:
            self._pc.stop()
        self._last_hover_ts = None

    # --- Pane B relayout (preserve zoom/pan ranges) ---
    def _on_paneB_relayout(self, event):
        # Robustly extract ranges/autorange from relayout payloads emitted by Plotly
        try:
            data = event.new or {}

            # X axis: support 'xaxis.range', 'xaxis.range[0/1]', 'xaxis.autorange'
            if 'xaxis.range[0]' in data and 'xaxis.range[1]' in data:
                self._current_x_range = (float(data['xaxis.range[0]']), float(data['xaxis.range[1]']))
                self._current_x_autorange = False
            elif 'xaxis.range' in data:
                rng = data.get('xaxis.range')
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    self._current_x_range = (float(rng[0]), float(rng[1]))
                    self._current_x_autorange = False
            elif 'xaxis.autorange' in data:
                # autorange True means clear explicit range
                self._current_x_autorange = bool(data.get('xaxis.autorange'))
                if self._current_x_autorange:
                    self._current_x_range = None

            # Y axis: same logic
            if 'yaxis.range[0]' in data and 'yaxis.range[1]' in data:
                self._current_y_range = (float(data['yaxis.range[0]']), float(data['yaxis.range[1]']))
                self._current_y_autorange = False
            elif 'yaxis.range' in data:
                rng = data.get('yaxis.range')
                if isinstance(rng, (list, tuple)) and len(rng) == 2:
                    self._current_y_range = (float(rng[0]), float(rng[1]))
                    self._current_y_autorange = False
            elif 'yaxis.autorange' in data:
                self._current_y_autorange = bool(data.get('yaxis.autorange'))
                if self._current_y_autorange:
                    self._current_y_range = None

            # Some Plotly versions emit nested keys or different payload shapes; handled permissively above.
        except Exception:
            # Ignore noisy relayout payloads
            pass

    def _apply_current_ranges(self, fig):
        """Apply stored ranges to fig if present."""
        try:
            # Only set explicit ranges when available. Only set autorange when explicitly known.
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
        # Ensure we operate on a go.Figure to apply ranges reliably
        try:
            fig_obj = fig if isinstance(fig, go.Figure) else go.Figure(fig)
        except Exception:
            # fallback: empty figure
            fig_obj = go.Figure()
        self._apply_current_ranges(fig_obj)
        return self._to_plotly(fig_obj)

    # --- Fitting and range behaviour ---
    def _on_fitting_clicked(self, event):
        self._fitting_active = not self._fitting_active
        self.fitting_button.name = f"Fitting: {'ON' if self._fitting_active else 'OFF'}"
        self.fitting_button.button_type = "danger" if self._fitting_active else "primary"
        if hasattr(self, 'range_slider_row'):
            self.range_slider_row.visible = self._fitting_active
        else:
            self.range_slider.visible = self._fitting_active

        # Mostrar/ocultar botón de multifit (coincide con fitting)
        self.multifit_button.visible = self._fitting_active

        # Refresh current view
        if self._region_pairs:
            fig = self._figB_region(self._region_pairs)
            if self._fitting_active:
                res = SpectrumExtractor.get_spectrum_from_indices(self._electron_count_data, self._region_pairs)
                if res is not None:
                    spec, _ = res
                y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return

        if self._last_hover_point is not None:
            fig = self._figB_hover(self._last_hover_point)
            if self._fitting_active:
                i, j = int(self._last_hover_point["y"]), int(self._last_hover_point["x"])
                spec = SpectrumExtractor.get_spectrum_from_pixel(self._electron_count_data, i, j)
                if spec is not None:
                    y_fit = SpectrumFitting.fit_powerlaw_curve(self._energy, spec, range_values=self.range_slider.value)
                    fig = self._plot_fit_traces(fig, self._energy, spec, y_fit)
            self.paneB.object = self._set_ranges_and_convert(fig)
            return

        self.paneB.object = self._set_ranges_and_convert(self._figB_message("Fitting", "Modo fitting: " + ("activado" if self._fitting_active else "desactivado")))