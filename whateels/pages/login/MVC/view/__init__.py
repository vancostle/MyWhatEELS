from .layouts import LoginMainLayout
import panel as pn

class LoginPageView:
    
    def __init__(self, model):
        
        # Load any provided CSS files
        pn.config.css_files.append('/assets/css/login.css') # type: ignore

        self._main = LoginMainLayout(
            width=400, 
            sizing_mode="stretch_both",
            styles={"height": "auto", "min-height": "auto"}
        )

    @property
    def main(self):
        return self._main