import panel as pn
import plotly.graph_objs as go
import numpy as np

from whateels.components import SplitJs, ModalManager

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from whateels.components import CustomPage

class DemoPageView:
    
    _STRETCH_BOTH = 'stretch_both'
    _STRETCH_WIDTH = 'stretch_width'
    
    def __init__(self, model, custom_page : "CustomPage") -> None:
        self._left_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        self._right_sidebar = pn.Column(sizing_mode=self._STRETCH_WIDTH)
        
        self._modal_manager = ModalManager(custom_page)
        
        modal_content_0 = pn.Column(
            pn.pane.Markdown("""
            ## Demo Modal Dialog
            This is a demo modal dialog content.
            """),
            width=400,
            height=200
        )
        self._modal_manager.add_modal("demo_modal_0", modal_content_0)
        
        modal_content_1 = pn.Column(
            pn.pane.Markdown("""
            ## Another modal dialog
            This is another modal dialog with different content.
            """),
            width=400,
            height=200
        )
        self._modal_manager.add_modal("demo_modal_1", modal_content_1)
        
        open_modal_button = pn.widgets.Button(name="Open Modal", button_type="primary")
        open_modal_button.on_click(lambda event: self._modal_manager.open("demo_modal_0"))
        self._left_sidebar.append(open_modal_button)
        
        open_modal_button_1 = pn.widgets.Button(name="Open Another Modal", button_type="primary")
        open_modal_button_1.on_click(lambda event: self._modal_manager.open("demo_modal_1"))
        self._left_sidebar.append(open_modal_button_1)
        
        # Simple heatmap (like paneA in spectrum_image_plot)
        ny, nx = 50, 50
        m_image = np.random.rand(ny, nx) * 100
        
        figA = go.Figure(data=[go.Heatmap(
            z=m_image,
            colorscale="Greys_r",
            showscale=False
        )])
        figA.update_layout(
            margin=dict(l=16, r=16, t=50, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        figA.update_yaxes(
            autorange="reversed", 
            showgrid=False, 
            zeroline=False, 
            showticklabels=False,
            scaleanchor="x", 
            scaleratio=1,
            constrain='domain'
        )
        figA.update_xaxes(showgrid=False, zeroline=False, showticklabels=False)
        
        self.paneA = pn.pane.Plotly(
            figA,
            config={"responsive": True},
            sizing_mode='stretch_both',
            margin=0
        )
        
        # Simple line chart (like paneB in spectrum_image_plot)
        energy = np.linspace(0, 100, 200)
        spectrum = np.random.rand(200) * 1000
        
        figB = go.Figure(data=[go.Scatter(
            x=energy,
            y=spectrum,
            mode="lines"
        )])
        figB.update_layout(
            title="Spectrum",
            margin=dict(l=16, r=16, t=48, b=16),
            xaxis_title="Energy Loss (eV)",
            yaxis_title="Intensity (a.u.)"
        )
        
        self.paneB = pn.pane.Plotly(
            figB,
            config={"responsive": True},
            sizing_mode='stretch_both',
            margin=0
        )
        
        splitjswrapper = SplitJs(
            left_column=pn.Column(
                self.paneA,
                sizing_mode=self._STRETCH_BOTH,
            ),
            right_column=pn.Column(
                self.paneB,
                sizing_mode=self._STRETCH_BOTH,
            ),
            sizing_mode=self._STRETCH_BOTH,
        )
        
        wrapper = pn.Row(
            self.paneA,
            self.paneB,
            sizing_mode=self._STRETCH_BOTH,
        )
        
        self._main = pn.Column(
            splitjswrapper,
            # wrapper,
            sizing_mode=self._STRETCH_BOTH
        )
        
    @property
    def main(self) -> pn.Column:
        return self._main
    
    @property
    def left_sidebar(self) -> pn.Column:
        return self._left_sidebar
    
    @property
    def right_sidebar(self) -> pn.Column:
        return self._right_sidebar
    
    @property
    def modal_manager(self) -> ModalManager:
        return self._modal_manager